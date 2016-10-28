import io

from lxml import etree

from tests.utils import DummyTransport, assert_nodes_equal, load_xml
from zeep import xsd


def get_transport():
    transport = DummyTransport()
    transport.bind(
        'http://schemas.xmlsoap.org/soap/encoding/',
        load_xml(io.open('tests/wsdl_files/soap-enc.xsd', 'r').read().encode('utf-8')))
    return transport


def test_simple_type():
    schema = xsd.Schema(load_xml("""
    <xsd:schema
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
        xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
        targetNamespace="http://tests.python-zeep.org/tns">
      <xsd:import namespace="http://schemas.xmlsoap.org/soap/encoding/"/>
      <xsd:complexType name="ArrayOfString">
        <xsd:complexContent>
          <xsd:restriction base="SOAP-ENC:Array">
            <xsd:attribute ref="SOAP-ENC:arrayType" wsdl:arrayType="xsd:string[]"/>
          </xsd:restriction>
        </xsd:complexContent>
      </xsd:complexType>
    </xsd:schema>
    """), transport=get_transport())

    ArrayOfString = schema.get_type('ns0:ArrayOfString')
    print(ArrayOfString.__dict__)

    value = ArrayOfString(['item', 'and', 'even', 'more', 'items'])

    node = etree.Element('document')
    ArrayOfString.render(node, value)

    expected = """
        <document>
            <item xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">item</item>
            <item xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">and</item>
            <item xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">even</item>
            <item xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">more</item>
            <item xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">items</item>
        </document>
    """  # noqa

    assert_nodes_equal(expected, node)


def test_complex_type():
    schema = xsd.Schema(load_xml("""
    <xsd:schema
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
        xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
        xmlns:tns="http://tests.python-zeep.org/tns"
        targetNamespace="http://tests.python-zeep.org/tns">
      <xsd:import namespace="http://schemas.xmlsoap.org/soap/encoding/"/>

      <xsd:complexType name="ArrayObject">
        <xsd:sequence>
          <xsd:element name="attr_1" type="xsd:string"/>
          <xsd:element name="attr_2" type="xsd:string"/>
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="ArrayOfObject">
        <xsd:complexContent>
          <xsd:restriction base="SOAP-ENC:Array">
            <xsd:sequence>
              <xsd:element name="obj" type="tns:ArrayObject" minOccurs="0" maxOccurs="unbounded"/>
            </xsd:sequence>
            <xsd:attribute ref="SOAP-ENC:arrayType" wsdl:arrayType="tns:ArrayObject[]"/>
          </xsd:restriction>
        </xsd:complexContent>
      </xsd:complexType>
    </xsd:schema>
    """), transport=get_transport())

    ArrayOfObject = schema.get_type('ns0:ArrayOfObject')
    ArrayObject = schema.get_type('ns0:ArrayObject')

    value = ArrayOfObject([
        ArrayObject(attr_1='attr-1', attr_2='attr-2'),
        ArrayObject(attr_1='attr-3', attr_2='attr-4'),
        ArrayObject(attr_1='attr-5', attr_2='attr-6'),
    ])

    node = etree.Element('document')
    ArrayOfObject.render(node, value)

    expected = """
        <document>
            <obj>
                <attr_1>attr-1</attr_1>
                <attr_2>attr-2</attr_2>
            </obj>
            <obj>
                <attr_1>attr-3</attr_1>
                <attr_2>attr-4</attr_2>
            </obj>
            <obj>
                <attr_1>attr-5</attr_1>
                <attr_2>attr-6</attr_2>
            </obj>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_complex_type_without_name():
    schema = xsd.Schema(load_xml("""
    <xsd:schema
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
        xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
        xmlns:tns="http://tests.python-zeep.org/tns"
        targetNamespace="http://tests.python-zeep.org/tns">
      <xsd:import namespace="http://schemas.xmlsoap.org/soap/encoding/"/>

      <xsd:complexType name="ArrayObject">
        <xsd:sequence>
          <xsd:element name="attr_1" type="xsd:string"/>
          <xsd:element name="attr_2" type="xsd:string"/>
        </xsd:sequence>
      </xsd:complexType>
      <xsd:complexType name="ArrayOfObject">
        <xsd:complexContent>
          <xsd:restriction base="SOAP-ENC:Array">
            <xsd:attribute ref="SOAP-ENC:arrayType" wsdl:arrayType="tns:ArrayObject[]"/>
          </xsd:restriction>
        </xsd:complexContent>
      </xsd:complexType>
    </xsd:schema>
    """), transport=get_transport())

    ArrayOfObject = schema.get_type('ns0:ArrayOfObject')
    ArrayObject = schema.get_type('ns0:ArrayObject')

    value = ArrayOfObject([
        ArrayObject(attr_1='attr-1', attr_2='attr-2'),
        ArrayObject(attr_1='attr-3', attr_2='attr-4'),
        ArrayObject(attr_1='attr-5', attr_2='attr-6'),
    ])

    node = etree.Element('document')
    ArrayOfObject.render(node, value)

    expected = """
        <document>
            <ArrayObject>
                <attr_1>attr-1</attr_1>
                <attr_2>attr-2</attr_2>
            </ArrayObject>
            <ArrayObject>
                <attr_1>attr-3</attr_1>
                <attr_2>attr-4</attr_2>
            </ArrayObject>
            <ArrayObject>
                <attr_1>attr-5</attr_1>
                <attr_2>attr-6</attr_2>
            </ArrayObject>
        </document>
    """
    assert_nodes_equal(expected, node)
