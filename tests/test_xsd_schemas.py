from lxml import etree

from zeep import xsd


class DummyTransport(object):
    def __init__(self):
        self._items = {}

    def bind(self, url, node):
        self._items[url] = node

    def load(self, url):
        return etree.tostring(self._items[url])


def test_multiple_extension():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

            <xs:import namespace="http://tests.python-zeep.org/b"/>

            <xs:complexType name="type_a">
              <xs:complexContent>
                <xs:extension base="b:type_b"/>
              </xs:complexContent>
            </xs:complexType>
            <xs:element name="typetje" type="tns:type_a"/>

        </xs:schema>
    """.strip())

    node_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            targetNamespace="http://tests.python-zeep.org/b"
            xmlns:c="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:import namespace="http://tests.python-zeep.org/c"/>

            <xs:complexType name="type_b">
              <xs:complexContent>
                <xs:extension base="c:type_c"/>
              </xs:complexContent>
            </xs:complexType>
        </xs:schema>
    """.strip())

    node_c = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/c"
            targetNamespace="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:import namespace="http://tests.python-zeep.org/c"/>

            <xs:complexType name="type_c">
                <xs:attribute name="wat" type="xs:string" />
            </xs:complexType>
        </xs:schema>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/b', node_b)
    transport.bind('http://tests.python-zeep.org/c', node_c)

    schema = xsd.Schema(node_a, transport=transport)
    type_a = schema.get_type('ns0:type_a')
    type_a(wat='x')
