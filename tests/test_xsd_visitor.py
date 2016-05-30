import pytest
from lxml import etree

from tests.utils import assert_nodes_equal, load_xml, render_node
from zeep.xsd import ListElement, builtins, visitor
from zeep.xsd.schema import Schema
from zeep.xsd.types import UnresolvedType


@pytest.fixture
def schema_visitor():
    schema = Schema()
    return visitor.SchemaVisitor(schema)


def test_schema_empty(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
              targetNamespace="http://tests.python-zeep.org/"
              elementFormDefault="qualified"
              attributeFormDefault="unqualified">
        </schema>
    """)
    schema_visitor.visit_schema(node)
    assert schema_visitor.schema._element_form == 'qualified'
    assert schema_visitor.schema._attribute_form == 'unqualified'


def test_element_simle_types(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
              targetNamespace="http://tests.python-zeep.org/">
            <element name="foo" type="string" />
            <element name="bar" type="int" />
        </schema>
    """)
    schema_visitor.visit_schema(node)
    assert len(schema_visitor.schema._elm_instances) == 2


def test_element_simple_type_annotation(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
              targetNamespace="http://tests.python-zeep.org/">
            <element name="foo" type="string">
                <annotation>
                    <documentation>HOI!</documentation>
                </annotation>
            </element>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    assert len(schema_visitor.schema._elm_instances) == 1


def test_element_default_type(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/">
            <element name="foo" />
        </schema>
    """)
    schema_visitor.visit_schema(node)
    element = schema_visitor.schema._elm_instances[0]
    assert isinstance(element.type, builtins.AnyType)


def test_element_simple_type_unresolved(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/">
            <element name="foo" type="tns:unresolved">
                <annotation>
                    <documentation>HOI!</documentation>
                </annotation>
            </element>
            <simpleType name="unresolved">
                <restriction base="integer">
                    <minInclusive value="0"/>
                    <maxInclusive value="100"/>
                </restriction>
            </simpleType>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    element = schema_visitor.schema._elm_instances[0]
    assert isinstance(element.type, UnresolvedType)
    assert element.type.qname == etree.QName(
        'http://tests.python-zeep.org/', 'unresolved')


def test_element_max_occurs(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
              targetNamespace="http://tests.python-zeep.org/">
            <element name="container">
                <complexType>
                    <sequence>
                        <element name="e1" type="string" />
                        <element name="e2" type="string" maxOccurs="1" />
                        <element name="e3" type="string" maxOccurs="2" />
                        <element name="e4" type="string" maxOccurs="unbounded" />
                    </sequence>
                </complexType>
            </element>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    elements = {elm.name: elm for elm in schema_visitor.schema._elm_instances}

    assert not isinstance(elements['e1'], ListElement)
    assert not isinstance(elements['e2'], ListElement)
    assert isinstance(elements['e3'], ListElement)
    assert isinstance(elements['e4'], ListElement)


def test_simple_content(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                targetNamespace="http://tests.python-zeep.org/">
            <complexType name="container">
                <simpleContent>
                    <extension base="xsd:string">
                        <attribute name="sizing" type="xsd:string" />
                    </extension>
                </simpleContent>
            </complexType>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    xsd_type = schema_visitor.schema.get_type(
        '{http://tests.python-zeep.org/}container')
    assert xsd_type(10, sizing='qwe')


def test_attribute_optional(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="foo">
            <complexType>
              <xsd:attribute name="base" type="xsd:string" />
            </complexType>
          </element>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    xsd_element = schema_visitor.schema.get_element(
        '{http://tests.python-zeep.org/}foo')
    value = xsd_element()

    node = render_node(xsd_element, value)
    expected = """
      <document>
        <ns0:foo xmlns:ns0="http://tests.python-zeep.org/"/>
      </document>
    """
    assert_nodes_equal(expected, node)


def test_attribute_required(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="foo">
            <complexType>
              <xsd:attribute name="base" use="required" type="xsd:string" />
            </complexType>
          </element>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    xsd_element = schema_visitor.schema.get_element(
        '{http://tests.python-zeep.org/}foo')
    value = xsd_element()

    node = render_node(xsd_element, value)
    expected = """
      <document>
        <ns0:foo xmlns:ns0="http://tests.python-zeep.org/" base=""/>
      </document>
    """
    assert_nodes_equal(expected, node)


def test_attribute_default(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="foo">
            <complexType>
              <xsd:attribute name="base" default="x" type="xsd:string" />
            </complexType>
          </element>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    xsd_element = schema_visitor.schema.get_element(
        '{http://tests.python-zeep.org/}foo')
    value = xsd_element()

    node = render_node(xsd_element, value)
    expected = """
      <document>
        <ns0:foo xmlns:ns0="http://tests.python-zeep.org/" base="x"/>
      </document>
    """
    assert_nodes_equal(expected, node)


def test_attribute_simple_type(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                targetNamespace="http://tests.python-zeep.org/">
            <element name="foo">
              <complexType>
                <attribute name="bar" use="optional">
                 <simpleType>
                  <restriction base="string">
                   <enumeration value="hoi"/>
                   <enumeration value="doei"/>
                  </restriction>
                 </simpleType>
                </attribute>
            </complexType>
          </element>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    xsd_element = schema_visitor.schema.get_element(
        '{http://tests.python-zeep.org/}foo')
    assert xsd_element(bar='hoi')


def test_attribute_any_type(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="foo">
            <complexType>
              <xsd:attribute name="base" type="xsd:anyURI" />
            </complexType>
          </element>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    xsd_element = schema_visitor.schema.get_element(
        '{http://tests.python-zeep.org/}foo')
    value = xsd_element(base='hoi')

    node = render_node(xsd_element, value)
    expected = """
      <document>
        <ns0:foo xmlns:ns0="http://tests.python-zeep.org/" base="hoi"/>
      </document>
    """
    assert_nodes_equal(expected, node)


def test_complex_content_mixed(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="foo">
            <xsd:complexType>
              <xsd:complexContent mixed="true">
                <xsd:extension base="xsd:anyType">
                  <xsd:attribute name="bar" type="xsd:anyURI" use="required"/>
                </xsd:extension>
              </xsd:complexContent>
            </xsd:complexType>
          </xsd:element>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    xsd_element = schema_visitor.schema.get_element(
        '{http://tests.python-zeep.org/}foo')
    result = xsd_element('basetype', bar='hoi')

    node = etree.Element('document')
    xsd_element.render(node, result)

    expected = """
      <document>
        <ns0:foo xmlns:ns0="http://tests.python-zeep.org/" bar="hoi">basetype</ns0:foo>
      </document>
    """
    assert_nodes_equal(expected, node)


def test_complex_content_extension(schema_visitor):
    node = load_xml("""
        <schema
                xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <complexType name="BaseType" abstract="true">
            <sequence>
              <element name="name" type="xsd:string" minOccurs="0"/>
            </sequence>
          </complexType>
          <complexType name="SubType1">
            <complexContent>
              <extension base="tns:BaseType">
                <attribute name="attr_1" type="xsd:string"/>
                <attribute name="attr_2" type="xsd:string"/>
              </extension>
            </complexContent>
          </complexType>
          <complexType name="SubType2">
            <complexContent>
              <extension base="tns:BaseType">
                <attribute name="attr_a" type="xsd:string"/>
                <attribute name="attr_b" type="xsd:string"/>
                <attribute name="attr_c" type="xsd:string"/>
              </extension>
            </complexContent>
          </complexType>
          <element name="test" type="tns:BaseType"/>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    schema = schema_visitor.schema
    schema._prefix_map['ns0'] = 'http://tests.python-zeep.org/'

    record_type = schema.get_type('ns0:SubType1')
    child_attrs = [child.name for child in record_type._children]
    assert len(child_attrs) == 3

    record_type = schema.get_type('ns0:SubType2')
    child_attrs = [child.name for child in record_type._children]
    assert len(child_attrs) == 4

    xsd_element = schema.get_element('ns0:test')
    xsd_type = schema.get_type('ns0:SubType2')

    value = xsd_type(attr_a='a', attr_b='b', attr_c='c')
    node = render_node(xsd_element, value)
    expected = """
      <document>
        <ns0:test
            xmlns:ns0="http://tests.python-zeep.org/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            attr_a="a" attr_b="b" attr_c="c" xsi:type="ns0:SubType2"/>
      </document>
    """
    assert_nodes_equal(expected, node)


def test_simple_content_extension(schema_visitor):
    node = load_xml("""
        <schema
                xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <simpleType name="BaseType">
            <restriction base="xsd:integer">
              <minInclusive value="0"/>
              <maxInclusive value="100"/>
            </restriction>
          </simpleType>
          <complexType name="SubType1">
            <simpleContent>
              <extension base="tns:BaseType">
                <attribute name="attr_1" type="xsd:string"/>
                <attribute name="attr_2" type="xsd:string"/>
              </extension>
            </simpleContent>
          </complexType>
          <complexType name="SubType2">
            <simpleContent>
              <extension base="tns:BaseType">
                <attribute name="attr_a" type="xsd:string"/>
                <attribute name="attr_b" type="xsd:string"/>
                <attribute name="attr_c" type="xsd:string"/>
              </extension>
            </simpleContent>
          </complexType>
        </schema>
    """)
    schema_visitor.visit_schema(node)
    schema = schema_visitor.schema
    schema._prefix_map['ns0'] = 'http://tests.python-zeep.org/'

    record_type = schema.get_type('ns0:SubType1')
    child_attrs = [child.name for child in record_type._children]
    assert len(child_attrs) == 3

    record_type = schema.get_type('ns0:SubType2')
    child_attrs = [child.name for child in record_type._children]
    assert len(child_attrs) == 4


def test_union_type(schema_visitor):
    node = load_xml("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:simpleType name="type">
            <xsd:union memberTypes="xsd:language">
              <xsd:simpleType>
                <xsd:restriction base="xsd:string">
                  <xsd:enumeration value=""/>
                </xsd:restriction>
              </xsd:simpleType>
            </xsd:union>
          </xsd:simpleType>

          <xsd:element name="foo">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="arg" type="tns:type"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </schema>
    """)

    schema_visitor.visit_schema(node)
    xsd_element = schema_visitor.schema.get_element(
        '{http://tests.python-zeep.org/}foo')
    assert xsd_element(arg='hoi')
