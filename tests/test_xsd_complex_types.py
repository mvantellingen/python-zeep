import pytest

from tests.utils import assert_nodes_equal, load_xml, render_node
from zeep import xsd


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
