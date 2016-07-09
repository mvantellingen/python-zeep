import datetime
from collections import OrderedDict

from lxml import etree

from tests.utils import assert_nodes_equal, load_xml
from zeep import xsd


def test_complex_type_alt():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="Address">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="1" name="foo" type="string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('ns0:Address')
    obj = address_type(foo='bar')

    expected = """
      <document>
        <ns0:Address xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:foo>bar</ns0:foo>
        </ns0:Address>
      </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_element_with_annotation():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="Address" type="tns:AddressType">
              <annotation>
                  <documentation>HOI!</documentation>
              </annotation>
          </element>
          <complexType name="AddressType">
            <sequence>
              <element minOccurs="0" maxOccurs="unbounded" name="foo" type="string" />
            </sequence>
          </complexType>
        </schema>
    """.strip())
    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    address_type(foo='bar')


def test_complex_type_parsexml():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="Address">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="1" name="foo" type="string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    input_node = etree.fromstring("""
        <Address xmlns="http://tests.python-zeep.org/">
          <foo>bar</foo>
        </Address>
    """)

    obj = address_type.parse(input_node, None)
    assert obj.foo == 'bar'


def test_complex_type_array_parsexml():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="container">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="unbounded" name="foo" type="string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}container')

    input_node = etree.fromstring("""
        <Address xmlns="http://tests.python-zeep.org/">
          <foo>bar</foo>
          <foo>zoo</foo>
        </Address>
    """)

    obj = address_type.parse(input_node, None)
    assert obj.foo == ['bar', 'zoo']


def test_array():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="Address">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="unbounded" name="foo" type="string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type()
    assert obj.foo == []
    obj.foo.append('foo')
    obj.foo.append('bar')

    expected = """
        <document>
          <ns0:Address xmlns:ns0="http://tests.python-zeep.org/">
            <ns0:foo>foo</ns0:foo>
            <ns0:foo>bar</ns0:foo>
          </ns0:Address>
        </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_complex_type_unbounded_one():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="Address">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="unbounded" name="foo" type="string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(foo=['foo'])

    expected = """
        <document>
          <ns0:Address xmlns:ns0="http://tests.python-zeep.org/">
            <ns0:foo>foo</ns0:foo>
          </ns0:Address>
        </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_complex_type_unbounded_named():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="Address" type="tns:AddressType" />
          <complexType name="AddressType">
            <sequence>
              <element minOccurs="0" maxOccurs="unbounded" name="foo" type="string" />
            </sequence>
          </complexType>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type()
    assert obj.foo == []
    obj.foo.append('foo')
    obj.foo.append('bar')

    expected = """
        <document>
          <ns0:Address xmlns:ns0="http://tests.python-zeep.org/">
            <ns0:foo>foo</ns0:foo>
            <ns0:foo>bar</ns0:foo>
          </ns0:Address>
        </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_complex_type_array_to_other_complex_object():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
          <xs:complexType name="Address">
            <xs:sequence>
              <xs:element minOccurs="0" maxOccurs="1" name="foo" type="xs:string" />
            </xs:sequence>
          </xs:complexType>
          <xs:complexType name="ArrayOfAddress">
            <xs:sequence>
              <xs:element minOccurs="0" maxOccurs="unbounded" name="Address" nillable="true" type="Address" />
            </xs:sequence>
          </xs:complexType>
          <xs:element name="ArrayOfAddress" type="ArrayOfAddress"/>
        </xs:schema>
    """.strip())  # noqa

    schema = xsd.Schema(node)
    address_array = schema.get_element('ArrayOfAddress')
    obj = address_array()
    assert obj.Address == []

    obj.Address.append(schema.get_type('Address')(foo='foo'))
    obj.Address.append(schema.get_type('Address')(foo='bar'))

    node = etree.fromstring("""
        <?xml version="1.0"?>
        <ArrayOfAddress>
            <Address>
                <foo>foo</foo>
            </Address>
            <Address>
                <foo>bar</foo>
            </Address>
        </ArrayOfAddress>
    """.strip())


def test_complex_type_init_kwargs():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="Address">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="1" name="NameFirst" type="string"/>
                <element minOccurs="0" maxOccurs="1" name="NameLast" type="string"/>
                <element minOccurs="0" maxOccurs="1" name="Email" type="string"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(
        NameFirst='John', NameLast='Doe', Email='j.doe@example.com')
    assert obj.NameFirst == 'John'
    assert obj.NameLast == 'Doe'
    assert obj.Email == 'j.doe@example.com'


def test_complex_type_init_args():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="Address">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="1" name="NameFirst" type="string"/>
                <element minOccurs="0" maxOccurs="1" name="NameLast" type="string"/>
                <element minOccurs="0" maxOccurs="1" name="Email" type="string"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type('John', 'Doe', 'j.doe@example.com')
    assert obj.NameFirst == 'John'
    assert obj.NameLast == 'Doe'
    assert obj.Email == 'j.doe@example.com'


def test_complex_type_with_attributes():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
          <xs:complexType name="Address">
            <xs:sequence>
              <xs:element minOccurs="0" maxOccurs="1" name="NameFirst" type="xs:string"/>
              <xs:element minOccurs="0" maxOccurs="1" name="NameLast" type="xs:string"/>
              <xs:element minOccurs="0" maxOccurs="1" name="Email" type="xs:string"/>
            </xs:sequence>
            <xs:attribute name="id" type="xs:string" use="required"/>
          </xs:complexType>
          <xs:element name="Address" type="Address"/>
        </xs:schema>
    """.strip())

    schema = xsd.Schema(node)

    address_type = schema.get_element('Address')
    obj = address_type(
        NameFirst='John', NameLast='Doe', Email='j.doe@example.com', id='123')

    node = etree.Element('document')
    address_type.render(node, obj)

    expected = """
        <document>
            <Address id="123">
                <NameFirst>John</NameFirst>
                <NameLast>Doe</NameLast>
                <Email>j.doe@example.com</Email>
            </Address>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_complex_type_with_extension():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/"
            elementFormDefault="qualified">

            <xs:complexType name="Address">
              <xs:complexContent>
                <xs:extension base="tns:Name">
                  <xs:sequence>
                    <xs:element name="country" type="xs:string"/>
                  </xs:sequence>
                </xs:extension>
              </xs:complexContent>
            </xs:complexType>
          <xs:element name="Address" type="tns:Address"/>

          <xs:complexType name="Name">
            <xs:sequence>
              <xs:element name="first_name" type="xs:string"/>
              <xs:element name="last_name" type="xs:string"/>
            </xs:sequence>
          </xs:complexType>
        </xs:schema>
    """.strip())
    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    obj = address_type(
        first_name='foo', last_name='bar', country='The Netherlands')

    node = etree.Element('document')
    address_type.render(node, obj)
    expected = """
        <document>
            <ns0:Address xmlns:ns0="http://tests.python-zeep.org/">
                <ns0:first_name>foo</ns0:first_name>
                <ns0:last_name>bar</ns0:last_name>
                <ns0:country>The Netherlands</ns0:country>
            </ns0:Address>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_complex_type_with_extension_nested():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/"
            elementFormDefault="qualified">

          <xs:element name="container" type="tns:baseResponse"/>
          <xs:complexType name="baseResponse">
            <xs:sequence>
              <xs:element name="item-1" type="xs:string"/>
              <xs:element name="item-2" type="xs:string"/>
            </xs:sequence>
          </xs:complexType>

          <xs:complexType name="response">
            <xs:complexContent>
              <xs:extension base="tns:baseResponse">
                <xs:sequence>
                  <xs:element name="item-3" type="xs:string"/>
                </xs:sequence>
              </xs:extension>
            </xs:complexContent>
          </xs:complexType>
        </xs:schema>
    """))
    elm_cls = schema.get_element('{http://tests.python-zeep.org/}container')

    node = load_xml("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance"
                       i:type="ns0:response">
            <ns0:item-1>item-1</ns0:item-1>
            <ns0:item-2>item-2</ns0:item-2>
            <ns0:item-3>item-3</ns0:item-3>
        </ns0:container>
    """)
    data = elm_cls.parse(node, schema)
    assert data['item-1'] == 'item-1'
    assert data['item-2'] == 'item-2'
    assert data['item-3'] == 'item-3'


def test_complex_type_simple_content():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/"
            elementFormDefault="qualified">

          <xs:element name="ShoeSize">
            <xs:complexType>
              <xs:simpleContent>
                <xs:extension base="xs:integer">
                  <xs:attribute name="sizing" type="xs:string" />
                </xs:extension>
              </xs:simpleContent>
            </xs:complexType>
          </xs:element>
        </xs:schema>
    """.strip())
    schema = xsd.Schema(node)
    shoe_type = schema.get_element('{http://tests.python-zeep.org/}ShoeSize')

    obj = shoe_type(20, sizing='EUR')

    node = etree.Element('document')
    shoe_type.render(node, obj)
    expected = """
        <document>
            <ns0:ShoeSize xmlns:ns0="http://tests.python-zeep.org/" sizing="EUR">20</ns0:ShoeSize>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_custom_simple_type():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="something">
            <simpleType>
              <restriction base="integer">
                <minInclusive value="0"/>
                <maxInclusive value="100"/>
              </restriction>
            </simpleType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)

    custom_type = schema.get_element('{http://tests.python-zeep.org/}something')
    obj = custom_type(75)

    node = etree.Element('document')
    custom_type.render(node, obj)
    expected = """
        <document>
            <ns0:something xmlns:ns0="http://tests.python-zeep.org/">75</ns0:something>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_group():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                   xmlns:tns="http://tests.python-zeep.org/"
                   targetNamespace="http://tests.python-zeep.org/"
                   elementFormDefault="qualified">

          <xs:element name="Address">
            <xs:complexType>
              <xs:group ref="tns:Name" />
            </xs:complexType>
          </xs:element>

          <xs:group name="Name">
            <xs:sequence>
              <xs:element name="first_name" type="xs:string" />
              <xs:element name="last_name" type="xs:string" />
            </xs:sequence>
          </xs:group>

        </xs:schema>
    """.strip())
    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    obj = address_type(first_name='foo', last_name='bar')

    node = etree.Element('document')
    address_type.render(node, obj)
    expected = """
        <document>
            <ns0:Address xmlns:ns0="http://tests.python-zeep.org/">
                <ns0:first_name>foo</ns0:first_name>
                <ns0:last_name>bar</ns0:last_name>
            </ns0:Address>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_group_for_type():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                   xmlns:tns="http://tests.python-zeep.org/"
                   targetNamespace="http://tests.python-zeep.org/"
                   elementFormDefault="unqualified">

          <xs:element name="Address" type="tns:AddressType" />

          <xs:complexType name="AddressType">
            <xs:sequence>
              <xs:group ref="tns:NameGroup"/>
              <xs:group ref="tns:AddressGroup"/>
            </xs:sequence>
          </xs:complexType>

          <xs:group name="NameGroup">
            <xs:sequence>
              <xs:element name="first_name" type="xs:string" />
              <xs:element name="last_name" type="xs:string" />
            </xs:sequence>
          </xs:group>

          <xs:group name="AddressGroup">
            <xs:annotation>
              <xs:documentation>blub</xs:documentation>
            </xs:annotation>
            <xs:sequence>
              <xs:element name="city" type="xs:string" />
              <xs:element name="country" type="xs:string" />
            </xs:sequence>
          </xs:group>
        </xs:schema>
    """.strip())
    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    obj = address_type(
        first_name='foo', last_name='bar',
        city='Utrecht', country='The Netherlands')

    node = etree.Element('document')
    address_type.render(node, obj)
    expected = """
        <document>
            <ns0:Address xmlns:ns0="http://tests.python-zeep.org/">
                <first_name>foo</first_name>
                <last_name>bar</last_name>
                <city>Utrecht</city>
                <country>The Netherlands</country>
            </ns0:Address>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_element_ref():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                   elementFormDefault="qualified">
          <element name="foo" type="string"/>
          <element name="bar">
            <complexType>
              <sequence>
                <element ref="tns:foo"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)

    foo_type = schema.get_element('{http://tests.python-zeep.org/}foo')
    assert isinstance(foo_type.type, xsd.String)

    custom_type = schema.get_element('{http://tests.python-zeep.org/}bar')
    custom_type.signature()
    obj = custom_type(foo='bar')

    node = etree.Element('document')
    custom_type.render(node, obj)
    expected = """
        <document>
            <ns0:bar xmlns:ns0="http://tests.python-zeep.org/">
                <ns0:foo>bar</ns0:foo>
            </ns0:bar>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_element_ref_occurs():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                   elementFormDefault="qualified">
          <element name="foo" type="string"/>
          <element name="bar">
            <complexType>
              <sequence>
                <element ref="tns:foo" minOccurs="0"/>
                <element name="bar" type="string"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)

    foo_type = schema.get_element('{http://tests.python-zeep.org/}foo')
    assert isinstance(foo_type.type, xsd.String)

    custom_type = schema.get_element('{http://tests.python-zeep.org/}bar')
    custom_type.signature()
    obj = custom_type(bar='foo')

    node = etree.Element('document')
    custom_type.render(node, obj)
    expected = """
        <document>
            <ns0:bar xmlns:ns0="http://tests.python-zeep.org/">
                <ns0:bar>foo</ns0:bar>
            </ns0:bar>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_element_any():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                   elementFormDefault="qualified">
          <element name="item" type="string"/>
          <element name="container">
            <complexType>
              <sequence>
                <element ref="tns:item"/>
                <any/>
                <any maxOccurs="unbounded"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)

    item_elm = schema.get_element('{http://tests.python-zeep.org/}item')
    assert isinstance(item_elm.type, xsd.String)

    container_elm = schema.get_element('{http://tests.python-zeep.org/}container')
    obj = container_elm(
        item='bar',
        _value_1=xsd.AnyObject(item_elm, item_elm('argh')))

    node = etree.Element('document')
    container_elm.render(node, obj)
    expected = """
        <document>
            <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
                <ns0:item>bar</ns0:item>
                <ns0:item>argh</ns0:item>
            </ns0:container>
        </document>
    """
    assert_nodes_equal(expected, node)
    item = container_elm.parse(node.getchildren()[0], schema)
    assert item.item == 'bar'
    assert item._value_1 == 'argh'


def test_element_any_parse():
    node = load_xml("""
        <xsd:schema
            elementFormDefault="qualified"
            targetNamespace="https://tests.python-zeep.org"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <xsd:element name="container">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:any/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """)

    schema = xsd.Schema(node)

    node = load_xml("""
          <container xmlns="https://tests.python-zeep.org">
            <something>
              <contains>text</contains>
            </something>
          </container>
    """)

    elm = schema.get_element('ns0:container')
    elm.parse(node, schema)


def test_element_any_type():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="container">
            <complexType>
              <sequence>
                <element name="something" type="anyType"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())
    schema = xsd.Schema(node)

    container_elm = schema.get_element('{http://tests.python-zeep.org/}container')
    obj = container_elm(something='bar')

    node = etree.Element('document')
    container_elm.render(node, obj)
    expected = """
        <document>
            <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
                <ns0:something>bar</ns0:something>
            </ns0:container>
        </document>
    """
    assert_nodes_equal(expected, node)
    item = container_elm.parse(node.getchildren()[0], schema)
    assert item.something == 'bar'


def test_any_in_nested_sequence():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            elementFormDefault="qualified"
            targetNamespace="http://tests.python-zeep.org/"
        >
          <xsd:element name="something" type="xsd:date"/>
          <xsd:element name="foobar" type="xsd:boolean"/>
          <xsd:element name="container">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="items" minOccurs="0">
                  <xsd:complexType>
                    <xsd:sequence>
                      <xsd:any namespace="##any" processContents="lax"/>
                    </xsd:sequence>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="version" type="xsd:string"/>
                <xsd:any namespace="##any" processContents="lax" minOccurs="0" maxOccurs="unbounded"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """))   # noqa

    container_elm = schema.get_element('{http://tests.python-zeep.org/}container')
    assert container_elm.signature() == (
        'items: {_value_1: ANY}, version: xsd:string, _value_1: ANY[]')

    something = schema.get_element('{http://tests.python-zeep.org/}something')
    foobar = schema.get_element('{http://tests.python-zeep.org/}foobar')

    any_1 = xsd.AnyObject(something, datetime.date(2016, 7, 4))
    any_2 = xsd.AnyObject(foobar, True)
    obj = container_elm(
        items={'_value_1': any_1}, version='str1234', _value_1=[any_1, any_2])

    node = etree.Element('document')
    container_elm.render(node, obj)
    expected = """
        <document>
          <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
            <ns0:items>
              <ns0:something>2016-07-04</ns0:something>
            </ns0:items>
            <ns0:version>str1234</ns0:version>
            <ns0:something>2016-07-04</ns0:something>
            <ns0:foobar>true</ns0:foobar>
          </ns0:container>
        </document>
    """
    assert_nodes_equal(expected, node)
    item = container_elm.parse(node.getchildren()[0], schema)
    assert item.items._value_1 == datetime.date(2016, 7, 4)
    assert item.version == 'str1234'
    assert item._value_1 == [datetime.date(2016, 7, 4), True]


def test_attribute_list_type():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <simpleType name="list">
            <list itemType="int"/>
          </simpleType>

          <element name="container">
            <complexType>
              <sequence>
                <element name="foo" type="xsd:string" />
              </sequence>
              <xsd:attribute name="lijst" type="tns:list"/>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    container_elm = schema.get_element('{http://tests.python-zeep.org/}container')
    assert container_elm.signature() == ('foo: xsd:string, lijst: xsd:int[]')
    obj = container_elm(foo='bar', lijst=[1, 2, 3])
    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/" lijst="1 2 3">
          <ns0:foo>bar</ns0:foo>
        </ns0:container>
      </document>
    """

    node = etree.Element('document')
    container_elm.render(node, obj)
    assert_nodes_equal(expected, node)

    item = container_elm.parse(node.getchildren()[0], schema)
    assert item.lijst == [1, 2, 3]
    assert item.foo == 'bar'


def test_anyattribute():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="container">
            <complexType>
              <sequence>
                <element name="foo" type="xsd:string" />
              </sequence>
              <xsd:anyAttribute processContents="lax"/>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    container_elm = schema.get_element('{http://tests.python-zeep.org/}container')
    assert container_elm.signature() == (
        'foo: xsd:string, _attr_1: {}')
    obj = container_elm(foo='bar', _attr_1=OrderedDict([
        ('hiep', 'hoi'), ('hoi', 'hiep')
    ]))

    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/" hiep="hoi" hoi="hiep">
          <ns0:foo>bar</ns0:foo>
        </ns0:container>
      </document>
    """

    node = etree.Element('document')
    container_elm.render(node, obj)
    assert_nodes_equal(expected, node)

    item = container_elm.parse(node.getchildren()[0], schema)
    assert item._attr_1 == {'hiep': 'hoi', 'hoi': 'hiep'}
    assert item.foo == 'bar'


def test_unqualified():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                attributeFormDefault="qualified"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="Address">
            <complexType>
              <sequence>
                <element name="foo" type="xsd:string" form="unqualified" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(foo='bar')

    expected = """
      <document>
        <ns0:Address xmlns:ns0="http://tests.python-zeep.org/">
          <foo>bar</foo>
        </ns0:Address>
      </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_qualified_attribute():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                attributeFormDefault="qualified"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="Address">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="foo" type="xsd:string" form="unqualified" />
              </xsd:sequence>
              <xsd:attribute name="id" type="xsd:string" use="required" form="unqualified" />
              <xsd:attribute name="pos" type="xsd:string" use="required" />
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(foo='bar', id="20", pos="30")

    expected = """
      <document>
        <ns0:Address xmlns:ns0="http://tests.python-zeep.org/" id="20" ns0:pos="30">
          <foo>bar</foo>
        </ns0:Address>
      </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_ref_attribute():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                attributeFormDefault="qualified"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="Address">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="foo" type="xsd:string" form="unqualified" />
              </xsd:sequence>
              <xsd:attribute ref="tns:id" use="required" />
            </xsd:complexType>
          </xsd:element>
          <xsd:attribute name="id" type="xsd:string" />
        </xsd:schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(foo='bar', id="hoi")

    expected = """
      <document>
        <ns0:Address xmlns:ns0="http://tests.python-zeep.org/" ns0:id="hoi">
          <foo>bar</foo>
        </ns0:Address>
      </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_defaults():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="container">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="foo" type="xsd:string" default="hoi"/>
              </xsd:sequence>
              <xsd:attribute name="bar" type="xsd:string" default="hoi"/>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """.strip())

    schema = xsd.Schema(node)
    container_type = schema.get_element(
        '{http://tests.python-zeep.org/}container')
    obj = container_type()
    assert obj.foo == "hoi"
    assert obj.bar == "hoi"

    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/" bar="hoi">
          <ns0:foo>hoi</ns0:foo>
        </ns0:container>
      </document>
    """
    node = etree.Element('document')
    container_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_defaults_parse():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="container">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="foo" type="xsd:string" default="hoi" minOccurs="0"/>
              </xsd:sequence>
              <xsd:attribute name="bar" type="xsd:string" default="hoi"/>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """.strip())

    schema = xsd.Schema(node)
    container_elm = schema.get_element(
        '{http://tests.python-zeep.org/}container')

    node = load_xml("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:foo>hoi</ns0:foo>
        </ns0:container>
    """)
    item = container_elm.parse(node, schema)
    assert item.bar == 'hoi'


def test_init_with_dicts():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                attributeFormDefault="qualified"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="Address">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="name" type="xsd:string"/>
                <xsd:element minOccurs="0" name="optional" type="xsd:string"/>
                <xsd:element name="container" nillable="true" type="tns:Container"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>

          <xsd:complexType name="Container">
            <xsd:sequence>
              <xsd:element maxOccurs="unbounded" minOccurs="0" name="service"
                           nillable="true" type="tns:ServiceRequestType"/>
            </xsd:sequence>
          </xsd:complexType>

          <xsd:complexType name="ServiceRequestType">
            <xsd:sequence>
              <xsd:element name="name" type="xsd:string"/>
            </xsd:sequence>
          </xsd:complexType>
        </xsd:schema>
    """.strip())

    schema = xsd.Schema(node)
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(name='foo', container={'service': [{'name': 'foo'}]})

    expected = """
      <document>
        <ns0:Address xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:name>foo</ns0:name>
          <ns0:container>
            <ns0:service>
              <ns0:name>foo</ns0:name>
            </ns0:service>
          </ns0:container>
        </ns0:Address>
      </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_complex_with_simple():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="Address">
            <xsd:complexType>
              <xsd:simpleContent>
                <xsd:extension base="tns:DateTimeType">
                  <xsd:attribute name="name" type="xsd:token"/>
                </xsd:extension>
              </xsd:simpleContent>
            </xsd:complexType>
          </xsd:element>

          <xsd:simpleType name="DateTimeType">
            <xsd:restriction base="xsd:dateTime"/>
          </xsd:simpleType>
        </xsd:schema>
    """.strip())
    schema = xsd.Schema(node)
    address_type = schema.get_element('ns0:Address')

    assert address_type.type.signature()
    val = datetime.datetime(2016, 5, 29, 11, 13, 45)
    obj = address_type(val, name='foobie')

    expected = """
      <document>
        <ns0:Address xmlns:ns0="http://tests.python-zeep.org/"
            name="foobie">2016-05-29T11:13:45</ns0:Address>
      </document>
    """
    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_sequence_with_type():
    node = load_xml("""
        <?xml version="1.0"?>
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
              </extension>
            </complexContent>
          </complexType>
          <complexType name="PolySequenceType">
            <sequence>
              <element name="item" type="tns:BaseType" maxOccurs="unbounded" minOccurs="0"/>
            </sequence>
          </complexType>
          <element name="Seq" type="tns:PolySequenceType"/>
        </schema>
    """)
    schema = xsd.Schema(node)
    seq = schema.get_type('ns0:PolySequenceType')
    sub_type = schema.get_type('ns0:SubType1')
    value = seq(item=[sub_type(attr_1="test", name="name")])

    node = etree.Element('document')
    seq.render(node, value)

    expected = """
      <document>
        <ns0:item
            xmlns:ns0="http://tests.python-zeep.org/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            attr_1="test" xsi:type="ns0:SubType1">
          <ns0:name>name</ns0:name>
        </ns0:item>
      </document>
    """
    assert_nodes_equal(expected, node)


def test_sequence_in_sequence():
    node = load_xml("""
        <?xml version="1.0"?>
        <schema
                xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="container">
            <complexType>
              <sequence>
                <sequence>
                  <element name="item_1" type="xsd:string"/>
                  <element name="item_2" type="xsd:string"/>
                </sequence>
              </sequence>
            </complexType>
          </element>
          <element name="foobar" type="xsd:string"/>
        </schema>
    """)
    schema = xsd.Schema(node)
    element = schema.get_element('ns0:container')
    value = element(item_1="foo", item_2="bar")

    node = etree.Element('document')
    element.render(node, value)

    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:container>
      </document>
    """
    assert_nodes_equal(expected, node)


def test_sequence_in_sequence_many():
    node = load_xml("""
        <?xml version="1.0"?>
        <schema
                xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <element name="container">
            <complexType>
              <sequence>
                <sequence minOccurs="2" maxOccurs="2">
                  <element name="item_1" type="xsd:string"/>
                  <element name="item_2" type="xsd:string"/>
                </sequence>
              </sequence>
            </complexType>
          </element>
          <element name="foobar" type="xsd:string"/>
        </schema>
    """)
    schema = xsd.Schema(node)
    element = schema.get_element('ns0:container')
    value = element(_value_1=[
        {'item_1': "value-1-1", 'item_2': "value-1-2"},
        {'item_1': "value-2-1", 'item_2': "value-2-2"},
    ])

    assert value._value_1 == [
        {'item_1': "value-1-1", 'item_2': "value-1-2"},
        {'item_1': "value-2-1", 'item_2': "value-2-2"},
    ]

    node = etree.Element('document')
    element.render(node, value)

    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>value-1-1</ns0:item_1>
          <ns0:item_2>value-1-2</ns0:item_2>
          <ns0:item_1>value-2-1</ns0:item_1>
          <ns0:item_2>value-2-2</ns0:item_2>
        </ns0:container>
      </document>
    """
    assert_nodes_equal(expected, node)


def test_complex_type_empty():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <complexType name="empty"/>
          <element name="container">
            <complexType>
              <sequence>
                <element name="something" type="tns:empty"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """.strip())

    schema = xsd.Schema(node)

    container_elm = schema.get_element('{http://tests.python-zeep.org/}container')
    obj = container_elm()

    node = etree.Element('document')
    container_elm.render(node, obj)
    expected = """
        <document>
            <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
                <ns0:something/>
            </ns0:container>
        </document>
    """
    assert_nodes_equal(expected, node)
    item = container_elm.parse(node.getchildren()[0], schema)
    assert item.something is None


def test_schema_as_payload():
    schema = xsd.Schema(load_xml("""
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <xsd:element name="container">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element ref="xsd:schema"/>
                <xsd:any/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """))
    elm_class = schema.get_element('{http://tests.python-zeep.org/}container')

    node = load_xml("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/"
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <xsd:schema
              targetNamespace="http://tests.python-zeep.org/inline-schema"
              elementFormDefault="qualified">
            <xsd:element name="sub-element">
              <xsd:complexType>
                <xsd:sequence>
                  <xsd:element name="item-1" type="xsd:string"/>
                  <xsd:element name="item-2" type="xsd:string"/>
                </xsd:sequence>
              </xsd:complexType>
            </xsd:element>
          </xsd:schema>
          <ns1:sub-element xmlns:ns1="http://tests.python-zeep.org/inline-schema">
            <ns1:item-1>value-1</ns1:item-1>
            <ns1:item-2>value-2</ns1:item-2>
          </ns1:sub-element>
        </ns0:container>
    """)
    value = elm_class.parse(node, schema)
    assert value._value_1['item-1'] == 'value-1'
    assert value._value_1['item-2'] == 'value-2'
