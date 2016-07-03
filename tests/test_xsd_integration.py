import datetime

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


def test_element_ref_in_choice():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                   elementFormDefault="qualified">
          <element name="foo" type="string"/>
          <element name="bar" type="string"/>
          <element name="bar">
            <complexType>
              <sequence>
                <choice>
                  <element ref="tns:foo"/>
                  <element ref="tns:bar"/>
                </choice>
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


def test_choice_element():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="container">
            <xsd:complexType>
              <xsd:choice>
                <xsd:element name="item_1" type="xsd:string" />
                <xsd:element name="item_2" type="xsd:string" />
                <xsd:element name="item_3" type="xsd:string" />
              </xsd:choice>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """.strip())
    schema = xsd.Schema(node)
    element = schema.get_element('ns0:container')
    value = element(item_1="foo")
    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
        </ns0:container>
      </document>
    """
    node = etree.Element('document')
    element.render(node, value)
    assert_nodes_equal(expected, node)


def test_choice_element_optional():
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
                <xsd:choice minOccurs="0">
                  <xsd:element name="item_1" type="xsd:string" />
                  <xsd:element name="item_2" type="xsd:string" />
                  <xsd:element name="item_3" type="xsd:string" />
                </xsd:choice>
                <xsd:element name="item_4" type="xsd:string" />
             </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """.strip())
    schema = xsd.Schema(node)
    element = schema.get_element('ns0:container')
    value = element(item_4="foo")

    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_4>foo</ns0:item_4>
        </ns0:container>
      </document>
    """
    node = etree.Element('document')
    element.render(node, value)
    assert_nodes_equal(expected, node)


def test_choice_nested_element():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="Address">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="something" type="xsd:string" />
                <xsd:choice>
                  <xsd:element name="item_1" type="xsd:string" />
                  <xsd:element name="item_2" type="xsd:string" />
                  <xsd:element name="item_3" type="xsd:string" />
                </xsd:choice>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """.strip())
    schema = xsd.Schema(node)
    address_type = schema.get_element('ns0:Address')

    assert address_type.type.signature() == (
        'something: xsd:string, _value_1: ({item_1: xsd:string} | {item_2: xsd:string} | {item_3: xsd:string})')  # noqa
    address_type(item_1="foo")


def test_choice_with_sequence():
    node = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name='ElementName'>
            <xsd:complexType xmlns:xsd="http://www.w3.org/2001/XMLSchema">
              <xsd:choice>
                <xsd:sequence>
                    <xsd:element name="UniqueElement-1" type="xsd:string"/>
                    <xsd:element name="UniqueElement-2" type="xsd:string"/>
                </xsd:sequence>
              </xsd:choice>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """)
    schema = xsd.Schema(node)
    element = schema.get_element('ns0:ElementName')
    assert element.type.signature() == (
        '({UniqueElement-1: xsd:string, UniqueElement-2: xsd:string})')

    element(**{'UniqueElement-1': 'foo', 'UniqueElement-2': 'bar'})


def test_choice_with_sequence_change():
    node = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name='ElementName'>
            <xsd:complexType xmlns:xsd="http://www.w3.org/2001/XMLSchema">
              <xsd:choice>
                <xsd:sequence>
                    <xsd:element name="UniqueElement-1" type="xsd:string"/>
                    <xsd:element name="UniqueElement-2" type="xsd:string"/>
                </xsd:sequence>
                <xsd:sequence>
                    <xsd:element name="UniqueElement-3" type="xsd:string"/>
                    <xsd:element name="UniqueElement-4" type="xsd:string"/>
                </xsd:sequence>
                <xsd:element name="nee" type="xsd:string"/>
              </xsd:choice>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """)
    schema = xsd.Schema(node)
    element = schema.get_element('ns0:ElementName')

    elm = element(
        **{'UniqueElement-1': 'foo', 'UniqueElement-2': 'bar'}
    )
    assert elm['UniqueElement-1'] == 'foo'
    assert elm['UniqueElement-2'] == 'bar'

    elm['UniqueElement-1'] = 'bla-1'
    elm['UniqueElement-2'] = 'bla-2'

    expected = """
      <document>
        <ns0:ElementName xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:UniqueElement-1>bla-1</ns0:UniqueElement-1>
          <ns0:UniqueElement-2>bla-2</ns0:UniqueElement-2>
        </ns0:ElementName>
      </document>
    """
    node = etree.Element('document')
    element.render(node, elm)
    assert_nodes_equal(expected, node)


def test_choice_with_sequence_change_named():
    node = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                elementFormDefault="qualified"
                targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name='ElementName'>
            <xsd:complexType xmlns:xsd="http://www.w3.org/2001/XMLSchema">
              <xsd:choice>
                <xsd:sequence>
                    <xsd:element name="UniqueElement-1" type="xsd:string"/>
                    <xsd:element name="UniqueElement-2" type="xsd:string"/>
                </xsd:sequence>
                <xsd:element name="UniqueElement-3" type="xsd:string"/>
              </xsd:choice>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """)
    schema = xsd.Schema(node)
    element = schema.get_element('ns0:ElementName')
    elm = element(
        **{'UniqueElement-3': 'foo'}
    )
    elm = element(
        **{'UniqueElement-1': 'foo', 'UniqueElement-2': 'bar'}
    )
    assert elm['UniqueElement-1'] == 'foo'
    assert elm['UniqueElement-2'] == 'bar'

    elm['UniqueElement-1'] = 'bla-1'
    elm['UniqueElement-2'] = 'bla-2'

    expected = """
      <document>
        <ns0:ElementName xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:UniqueElement-1>bla-1</ns0:UniqueElement-1>
          <ns0:UniqueElement-2>bla-2</ns0:UniqueElement-2>
        </ns0:ElementName>
      </document>
    """
    node = etree.Element('document')
    element.render(node, elm)
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
