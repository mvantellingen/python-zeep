from lxml import etree

from tests.utils import assert_nodes_equal
from zeep.wsdl import Schema


def test_complex_type_alt():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <schema xmlns="http://www.w3.org/2001/XMLSchema"
                  xmlns:tns="http://tests.python-zeep.org/"
                  targetNamespace="http://tests.python-zeep.org/">
            <element name="Address">
              <complexType>
                <sequence>
                  <element minOccurs="0" maxOccurs="1" name="foo" type="string" />
                </sequence>
              </complexType>
            </element>
          </schema>
        </types>
    """.strip())

    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(foo='bar')

    expected = """
      <document>
        <Address xmlns="http://tests.python-zeep.org/">
          <foo>bar</foo>
        </Address>
      </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_element_with_annotation():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <schema xmlns="http://www.w3.org/2001/XMLSchema"
                  xmlns:tns="http://tests.python-zeep.org/"
                  targetNamespace="http://tests.python-zeep.org/">
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
        </types>
    """.strip())
    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(foo='bar')


def test_complex_type_parsexml():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <schema xmlns="http://www.w3.org/2001/XMLSchema"
                  xmlns:tns="http://tests.python-zeep.org/"
                  targetNamespace="http://tests.python-zeep.org/">
            <element name="Address">
              <complexType>
                <sequence>
                  <element minOccurs="0" maxOccurs="1" name="foo" type="string" />
                </sequence>
              </complexType>
            </element>
          </schema>
        </types>
    """.strip())

    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    input_node = etree.fromstring("""
        <Address>
          <foo>bar</foo>
        </Address>
    """)

    obj = address_type.parse(input_node)
    assert obj.foo == 'bar'


def test_complex_type_array_parsexml():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <schema xmlns="http://www.w3.org/2001/XMLSchema"
                  xmlns:tns="http://tests.python-zeep.org/"
                  targetNamespace="http://tests.python-zeep.org/">
            <element name="Address">
              <complexType>
                <sequence>
                  <element minOccurs="0" maxOccurs="unbounded" name="foo" type="string" />
                </sequence>
              </complexType>
            </element>
          </schema>
        </types>
    """.strip())

    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    input_node = etree.fromstring("""
        <Address>
          <foo>bar</foo>
          <foo>zoo</foo>
        </Address>
    """)

    obj = address_type.parse(input_node)
    assert obj.foo == ['bar', 'zoo']


def test_array():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <schema xmlns="http://www.w3.org/2001/XMLSchema"
                  xmlns:tns="http://tests.python-zeep.org/"
                  targetNamespace="http://tests.python-zeep.org/">
            <element name="Address">
              <complexType>
                <sequence>
                  <element minOccurs="0" maxOccurs="unbounded" name="foo" type="string" />
                </sequence>
              </complexType>
            </element>
          </schema>
        </types>
    """.strip())

    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type()
    assert obj.foo == []
    obj.foo.append('foo')
    obj.foo.append('bar')

    expected = """
        <document>
          <Address xmlns="http://tests.python-zeep.org/">
            <foo>foo</foo>
            <foo>bar</foo>
          </Address>
        </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_array_resolve_lazy():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <schema xmlns="http://www.w3.org/2001/XMLSchema"
                  xmlns:tns="http://tests.python-zeep.org/"
                  targetNamespace="http://tests.python-zeep.org/">
            <element name="Address" type="tns:AddressType" />
            <complexType name="AddressType">
              <sequence>
                <element minOccurs="0" maxOccurs="unbounded" name="foo" type="string" />
              </sequence>
            </complexType>
          </schema>
        </types>
    """.strip())

    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type()
    assert obj.foo == []
    obj.foo.append('foo')
    obj.foo.append('bar')

    expected = """
        <document>
          <Address xmlns="http://tests.python-zeep.org/">
            <foo>foo</foo>
            <foo>bar</foo>
          </Address>
        </document>
    """

    node = etree.Element('document')
    address_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_complex_type_array_to_other_complex_object():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
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
        </types>
    """.strip())

    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_array = schema.get_element('ArrayOfAddress')
    obj = address_array()
    assert obj.Address == []

    obj.Address.append(schema.get_element('Address')(foo='foo'))
    obj.Address.append(schema.get_element('Address')(foo='bar'))

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


def test_decimal():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
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
        </types>
    """.strip())

    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(
        NameFirst='John', NameLast='Doe', Email='j.doe@example.com')


def test_complex_type_with_attributes():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
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
        </types>
    """.strip())

    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))

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


def test_custom_simple_type():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <schema xmlns="http://www.w3.org/2001/XMLSchema"
                  xmlns:tns="http://tests.python-zeep.org/"
                  targetNamespace="http://tests.python-zeep.org/">
            <element name="something">
              <simpleType>
                <restriction base="integer">
                  <minInclusive value="0"/>
                  <maxInclusive value="100"/>
                </restriction>
              </simpleType>
            </element>
          </schema>
        </types>
    """.strip())

    schema = Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))

    custom_type = schema.get_element('{http://tests.python-zeep.org/}something')
    obj = custom_type(75)

    node = etree.Element('document')
    custom_type.render(node, obj)
    expected = """
        <document>
            <something xmlns="http://tests.python-zeep.org/">75</something>
        </document>
    """
    assert_nodes_equal(expected, node)
