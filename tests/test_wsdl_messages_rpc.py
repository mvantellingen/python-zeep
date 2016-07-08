
from collections import OrderedDict

from lxml import etree
from pretend import stub
from six import StringIO

from tests.utils import assert_nodes_equal, load_xml
from zeep import xsd
from zeep.wsdl import definitions, messages, soap, wsdl


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
