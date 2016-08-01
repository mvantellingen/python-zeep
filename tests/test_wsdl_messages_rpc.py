import io
from six import StringIO

from tests.utils import DummyTransport, assert_nodes_equal, load_xml
from zeep.wsdl import wsdl


def test_serialize():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">

      <message name="Input">
        <part name="arg1" type="xsd:string"/>
        <part name="arg2" type="xsd:string"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="rpc" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="encoded"
                       namespace="http://test.python-zeep.org/tests/rpc"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    assert operation.input.signature() == 'arg1: xsd:string, arg2: xsd:string'

    serialized = operation.input.serialize(arg1='ah1', arg2='ah2')
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <soap-env:Body>
            <ns0:TestOperation xmlns:ns0="http://test.python-zeep.org/tests/rpc">
              <arg1>ah1</arg1>
              <arg2>ah2</arg2>
            </ns0:TestOperation>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_serialize_empty_input():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="tns:TestOperationRequests"/>
        </operation>
      </portType>

      <message name="TestOperationRequests"/>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="rpc" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="encoded"
                       namespace="http://test.python-zeep.org/tests/rpc"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    serialized = operation.input.serialize()
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <soap-env:Body>
            <ns0:TestOperation xmlns:ns0="http://test.python-zeep.org/tests/rpc"/>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_deserialize():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <message name="Output">
        <part name="result" type="xsd:string"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <output message="Output"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="rpc" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <output>
            <soap:body use="encoded"
                       namespace="http://test.python-zeep.org/tests/rpc"/>
          </output>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    document = load_xml("""
        <soap-env:Body
          xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <ns0:Output xmlns:ns0="http://test.python-zeep.org/tests/rpc">
            <result>ah1</result>
          </ns0:Output>
        </soap-env:Body>
    """)
    assert operation.output.signature(True) == 'xsd:string'
    result = operation.output.deserialize(document)
    assert result == 'ah1'


def test_wsdl_array_of_simple_types():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/" targetNamespace="http://tests.python-zeep.org/tns" xmlns:tns="http://tests.python-zeep.org/tns" xmlns:impl="http://tests.python-zeep.org/tns" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">
      <types>
        <schema xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://tests.python-zeep.org/tns">
          <complexType name="ArrayOfString">
            <complexContent>
              <restriction base="soapenc:Array">
                <attribute ref="soapenc:arrayType" wsdl:arrayType="xsd:string[]"/>
              </restriction>
            </complexContent>
          </complexType>
        </schema>
      </types>
      <portType name="SimpleTypeArrayPortType">
        <operation name="getSimpleArray">
          <input message="tns:getSimpleArrayRequest"/>
          <output message="tns:getSimpleArrayResponse"/>
        </operation>
      </portType>
      <binding name="SimpleTypeArrayBinding" type="tns:SimpleTypeArrayPortType">
        <soap:binding style="rpc" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="getSimpleArray">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="encoded" namespace="http://tests.python-zeep.org/tns" encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"/>
          </input>
          <output>
            <soap:body parts="return" use="encoded" namespace="http://tests.python-zeep.org/tns" encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"/>
          </output>
        </operation>
      </binding>
      <message name="getSimpleArrayRequest"/>
      <message name="getSimpleArrayResponse">
        <part name="return" type="tns:ArrayOfString"/>
      </message>
    </definitions>
    """.strip())

    transport = DummyTransport()
    transport.bind(
        'http://schemas.xmlsoap.org/soap/encoding/',
        load_xml(io.open('tests/wsdl_files/soap-enc.xsd', 'r').read().encode('utf-8')))
    root = wsdl.Document(wsdl_content, transport)

    binding = root.bindings['{http://tests.python-zeep.org/tns}SimpleTypeArrayBinding']
    operation = binding.get('getSimpleArray')

    document = load_xml("""
        <SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="http://tests.python-zeep.org/tns" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <ns1:getSimpleArrayResponse>
                <return SOAP-ENC:arrayType="xsd:string[16]" xsi:type="ns1:ArrayOfString">
                    <item xsi:type="xsd:string">item</item>
                    <item xsi:type="xsd:string">and</item>
                    <item xsi:type="xsd:string">even</item>
                    <item xsi:type="xsd:string">more</item>
                    <item xsi:type="xsd:string">items</item>
                </return>
            </ns1:getSimpleArrayResponse>
        </SOAP-ENV:Body>
    """)

    deserialized = operation.output.deserialize(document)
    list_of_items = deserialized['_value_1']

    assert list_of_items == ['item', 'and', 'even', 'more', 'items']
