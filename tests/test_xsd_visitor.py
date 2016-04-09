import pytest
from lxml import etree

from zeep.xsd import ListElement, builtins, visitor
from zeep.xsd.schema import Schema
from zeep.xsd.types import UnresolvedType


@pytest.fixture
def schema_visitor():
    schema = Schema()
    return visitor.SchemaVisitor(schema)


def create_node(text):
    node = etree.fromstring(text)
    etree.XMLSchema(node)
    return node


def test_schema_empty(schema_visitor):
    node = create_node("""
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
    node = create_node("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
              targetNamespace="http://tests.python-zeep.org/">
            <element name="foo" type="string" />
            <element name="bar" type="int" />
        </schema>
    """)
    schema_visitor.visit_schema(node)
    assert len(schema_visitor.schema._elm_instances) == 2


def test_element_simple_type_annotation(schema_visitor):
    node = create_node("""
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
    node = create_node("""
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/">
            <element name="foo" />
        </schema>
    """)
    schema_visitor.visit_schema(node)
    element = schema_visitor.schema._elm_instances[0]
    assert isinstance(element.type, builtins.String)


def test_element_simple_type_unresolved(schema_visitor):
    node = create_node("""
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
    node = create_node("""
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
    node = create_node("""
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


def test_attribute_simple_type(schema_visitor):
    node = create_node("""
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
