import pytest
from lxml import etree

from tests.utils import assert_nodes_equal, render_node
from zeep import xsd


def test_group_mixed():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'username'),
                    xsd.String()),
                xsd.Group(
                    etree.QName('http://tests.python-zeep.org/', 'groupie'),
                    xsd.Sequence([
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'password'),
                            xsd.String(),
                        )
                    ])
                )
            ])
        ))
    assert custom_type.signature()
    obj = custom_type(username='foo', password='bar')

    expected = """
      <document>
        <ns0:authentication xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:username>foo</ns0:username>
          <ns0:password>bar</ns0:password>
        </ns0:authentication>
      </document>
    """
    node = etree.Element('document')
    custom_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_group_optional():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Group(
                etree.QName('http://tests.python-zeep.org/', 'foobar'),
                xsd.Sequence([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_1'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_2'),
                        xsd.String()),
                ]),
                min_occurs=1)
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2 == 'bar'
    assert not hasattr(obj, 'foobar')


def test_group_min_occurs_2():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Group(
                etree.QName('http://tests.python-zeep.org/', 'foobar'),
                xsd.Sequence([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_1'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_2'),
                        xsd.String()),
                ]),
                min_occurs=2, max_occurs=2)
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj._value_1 == [
        {'item_1': 'foo', 'item_2': 'bar'},
        {'item_1': 'foo', 'item_2': 'bar'},
    ]
    assert not hasattr(obj, 'foobar')


def test_group_min_occurs_2_sequence_min_occurs_2():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Group(
                etree.QName('http://tests.python-zeep.org/', 'foobar'),
                xsd.Sequence([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_1'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_2'),
                        xsd.String()),
                ], min_occurs=2, max_occurs=2),
                min_occurs=2, max_occurs=2)
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj._value_1 == [
        {'_value_1': [
            {'item_1': 'foo', 'item_2': 'bar'},
            {'item_1': 'foo', 'item_2': 'bar'},
        ]},
        {'_value_1': [
            {'item_1': 'foo', 'item_2': 'bar'},
            {'item_1': 'foo', 'item_2': 'bar'},
        ]},
    ]
    assert not hasattr(obj, 'foobar')


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
