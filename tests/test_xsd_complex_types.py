import pytest

from lxml import etree
from tests.utils import assert_nodes_equal, load_xml, render_node
from zeep import xsd, exceptions


def test_single_node():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="container">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="1" name="item" type="string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """))
    schema.set_ns_prefix('tns', 'http://tests.python-zeep.org/')

    container_elm = schema.get_element('tns:container')
    obj = container_elm(item='bar')

    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item>bar</ns0:item>
        </ns0:container>
      </document>
    """
    result = render_node(container_elm, obj)
    assert_nodes_equal(result, expected)

    obj = container_elm.parse(result[0], schema)
    assert obj.item == 'bar'


def test_nested_sequence():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="container">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="1" name="item">
                  <complexType>
                    <sequence>
                      <element name="x" type="integer"/>
                      <element name="y" type="integer"/>
                    </sequence>
                  </complexType>
                </element>
              </sequence>
            </complexType>
          </element>
        </schema>
    """))
    schema.set_ns_prefix('tns', 'http://tests.python-zeep.org/')

    container_elm = schema.get_element('tns:container')
    obj = container_elm(item={'x': 1, 'y': 2})

    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item>
            <ns0:x>1</ns0:x>
            <ns0:y>2</ns0:y>
          </ns0:item>
        </ns0:container>
      </document>
    """
    result = render_node(container_elm, obj)
    assert_nodes_equal(result, expected)

    obj = container_elm.parse(result[0], schema)
    assert obj.item.x == 1
    assert obj.item.y == 2


def test_single_node_array():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="container">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="unbounded" name="item" type="string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """))
    schema.set_ns_prefix('tns', 'http://tests.python-zeep.org/')

    container_elm = schema.get_element('tns:container')
    obj = container_elm(item=['item-1', 'item-2', 'item-3'])
    assert obj.item == ['item-1', 'item-2', 'item-3']

    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item>item-1</ns0:item>
          <ns0:item>item-2</ns0:item>
          <ns0:item>item-3</ns0:item>
        </ns0:container>
      </document>
    """
    result = render_node(container_elm, obj)
    assert_nodes_equal(result, expected)

    obj = container_elm.parse(result[0], schema)
    assert obj.item == ['item-1', 'item-2', 'item-3']


def test_single_node_no_iterable():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="container">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="1" name="item" type="string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """))
    schema.set_ns_prefix('tns', 'http://tests.python-zeep.org/')

    container_elm = schema.get_element('tns:container')

    obj = container_elm(item=['item-1', 'item-2', 'item-3'])
    assert obj.item == ['item-1', 'item-2', 'item-3']

    with pytest.raises(ValueError):
        render_node(container_elm, obj)


def test_complex_any_types():
    # see https://github.com/mvantellingen/python-zeep/issues/252
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="container">
            <complexType>
              <sequence>
                <element minOccurs="0" maxOccurs="1" name="auth" type="anyType" />
                <element minOccurs="0" maxOccurs="1" name="params" type="anyType" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """))

    schema.set_ns_prefix('tns', 'http://tests.python-zeep.org/')
    KeyValueData = xsd.Element(
        '{http://xml.apache.org/xml-soap}KeyValueData',
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    'key',
                    xsd.AnyType(),
                ),
                xsd.Element(
                    'value',
                    xsd.AnyType(),
                ),
            ]),
        ),
    )

    Map = xsd.ComplexType(
        xsd.Sequence([
            xsd.Element(
                'item',
                xsd.AnyType(),
                min_occurs=1,
                max_occurs="unbounded"),
        ]),
        qname=etree.QName('{http://xml.apache.org/xml-soap}Map'))

    header_Username = KeyValueData(xsd.AnyObject(xsd.String(), 'Username'), value=xsd.AnyObject(xsd.String(), 'abc'))
    header_ShopId = KeyValueData(xsd.AnyObject(xsd.String(), 'ShopId'), value=xsd.AnyObject(xsd.Int(), 123))
    auth = Map(item=[header_Username, header_ShopId])

    header_LimitNum = KeyValueData(xsd.AnyObject(xsd.String(), 'LimitNum'), value=xsd.AnyObject(xsd.Int(), 2))
    params = Map(item=[header_LimitNum])

    container = schema.get_element('ns0:container')
    obj = container(auth=auth, params=params)

    result = render_node(container, obj)
    expected = load_xml("""
    <document>
      <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
        <ns0:auth xmlns:ns1="http://xml.apache.org/xml-soap" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="ns1:Map">
          <item>
            <key xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">Username</key>
            <value xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">abc</value>
          </item>
          <item>
            <key xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">ShopId</key>
            <value xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:int">123</value>
          </item>
        </ns0:auth>
        <ns0:params xmlns:ns2="http://xml.apache.org/xml-soap" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="ns2:Map">
          <item>
            <key xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">LimitNum</key>
            <value xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:int">2</value>
          </item>
        </ns0:params>
      </ns0:container>
    </document>
    """)  # noqa
    assert_nodes_equal(result, expected)
