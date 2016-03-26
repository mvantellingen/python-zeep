from lxml import etree

from tests.utils import assert_nodes_equal
from zeep import xsd


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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
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
    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    input_node = etree.fromstring("""
        <Address xmlns="http://tests.python-zeep.org/">
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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    input_node = etree.fromstring("""
        <Address xmlns="http://tests.python-zeep.org/">
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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
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


def test_complex_type_init_kwargs():
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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type(
        NameFirst='John', NameLast='Doe', Email='j.doe@example.com')
    assert obj.NameFirst == 'John'
    assert obj.NameLast == 'Doe'
    assert obj.Email == 'j.doe@example.com'


def test_complex_type_init_args():
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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')
    obj = address_type('John', 'Doe', 'j.doe@example.com')
    assert obj.NameFirst == 'John'
    assert obj.NameLast == 'Doe'
    assert obj.Email == 'j.doe@example.com'


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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))

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

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))

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


def test_group():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                     xmlns:tns="http://tests.python-zeep.org/"
                     targetNamespace="http://tests.python-zeep.org/">

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
        </types>
    """.strip())
    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    obj = address_type(first_name='foo', last_name='bar')

    node = etree.Element('document')
    address_type.render(node, obj)
    expected = """
        <document>
            <Address xmlns="http://tests.python-zeep.org/">
                <first_name>foo</first_name>
                <last_name>bar</last_name>
            </Address>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_group_for_type():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                     xmlns:tns="http://tests.python-zeep.org/"
                     targetNamespace="http://tests.python-zeep.org/">

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
        </types>
    """.strip())
    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))
    address_type = schema.get_element('{http://tests.python-zeep.org/}Address')

    obj = address_type(
        first_name='foo', last_name='bar',
        city='Utrecht', country='The Netherlands')

    node = etree.Element('document')
    address_type.render(node, obj)
    expected = """
        <document>
            <Address xmlns="http://tests.python-zeep.org/">
                <first_name>foo</first_name>
                <last_name>bar</last_name>
                <city>Utrecht</city>
                <country>The Netherlands</country>
            </Address>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_element_ref():
    node = etree.fromstring("""
        <?xml version="1.0"?>
        <types>
          <schema xmlns="http://www.w3.org/2001/XMLSchema"
                  xmlns:tns="http://tests.python-zeep.org/"
                  targetNamespace="http://tests.python-zeep.org/">
            <element name="foo" type="string"/>
            <element name="bar">
              <complexType>
                <sequence>
                  <element ref="tns:foo"/>
                </sequence>
              </complexType>
            </element>
          </schema>
        </types>
    """.strip())

    schema = xsd.Schema(node.find('{http://www.w3.org/2001/XMLSchema}schema'))

    foo_type = schema.get_element('{http://tests.python-zeep.org/}foo')
    assert isinstance(foo_type.type, xsd.String)

    custom_type = schema.get_element('{http://tests.python-zeep.org/}bar')
    obj = custom_type(foo='bar')

    node = etree.Element('document')
    custom_type.render(node, obj)
    expected = """
        <document>
            <bar xmlns="http://tests.python-zeep.org/">
                <foo>bar</foo>
            </bar>
        </document>
    """
    assert_nodes_equal(expected, node)
