from lxml import etree

from tests.utils import assert_nodes_equal, load_xml
from zeep import xsd


def test_simple_type():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="item">
            <complexType>
              <sequence>
                <element name="something" type="long"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """))

    item_cls = schema.get_element('{http://tests.python-zeep.org/}item')
    item = item_cls(something=12345678901234567890)

    node = etree.Element('document')
    item_cls.render(node, item)
    expected = """
        <document>
          <ns0:item xmlns:ns0="http://tests.python-zeep.org/">
            <ns0:something>12345678901234567890</ns0:something>
          </ns0:item>
        </document>
    """
    assert_nodes_equal(expected, node)
    item = item_cls.parse(node.getchildren()[0], schema)
    assert item.something == 12345678901234567890


def test_simple_type_optional():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="item">
            <complexType>
              <sequence>
                <element name="something" type="long" minOccurs="0"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """))

    item_cls = schema.get_element('{http://tests.python-zeep.org/}item')
    item = item_cls()
    assert item.something is None

    node = etree.Element('document')
    item_cls.render(node, item)
    expected = """
        <document>
          <ns0:item xmlns:ns0="http://tests.python-zeep.org/"/>
        </document>
    """
    assert_nodes_equal(expected, node)

    item = item_cls.parse(node.getchildren()[0], schema)
    assert item.something is None
