from six import StringIO
from collections import OrderedDict

from lxml import etree
from pretend import stub

from tests.utils import assert_nodes_equal, load_xml
from zeep import xsd
from zeep.wsdl import definitions, messages, soap
from zeep.wsdl import wsdl


def test_parse():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema targetNamespace="http://tests.python-zeep.org/tns">
          <xsd:element name="Request" type="xsd:string"/>
        </xsd:schema>
      </types>

      <message name="Input">
        <part element="tns:Request"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="literal"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    assert operation.input.body.signature() == 'xsd:string'


def test_parse_with_header():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema targetNamespace="http://tests.python-zeep.org/tns">
          <xsd:element name="Request" type="xsd:string"/>
          <xsd:element name="RequestHeader" type="xsd:string"/>
        </xsd:schema>
      </types>

      <message name="Input">
        <part element="tns:Request"/>
        <part name="header" element="tns:RequestHeader"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:header message="tns:Input" part="header" use="literal" />
            <soap:body use="literal"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    assert operation.input.headers.signature() == 'RequestHeader: RequestHeader()'
    assert operation.input.body.signature() == 'xsd:string'


def test_parse_with_header_other_message():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema targetNamespace="http://tests.python-zeep.org/tns">
          <xsd:element name="Request" type="xsd:string"/>
          <xsd:element name="RequestHeader" type="xsd:string"/>
        </xsd:schema>
      </types>

      <message name="InputHeader">
        <part name="header" element="tns:RequestHeader"/>
      </message>
      <message name="Input">
        <part element="tns:Request"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:header message="tns:InputHeader" part="header" use="literal" />
            <soap:body use="literal"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    assert operation.input.headers.signature() == 'RequestHeader: RequestHeader()'
    assert operation.input.body.signature() == 'xsd:string'

    header = root.types.get_element(
        '{http://tests.python-zeep.org/tns}RequestHeader'
    )('foo')
    serialized = operation.input.serialize(
        'ah1', _soapheaders={'RequestHeader': header})
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:ns0="http://tests.python-zeep.org/tns"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <soap-env:Header>
            <ns0:RequestHeader>foo</ns0:RequestHeader>
          </soap-env:Header>
          <soap-env:Body>
            <ns0:Request>ah1</ns0:Request>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_serialize():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema targetNamespace="http://tests.python-zeep.org/tns"
                    elementFormDefault="qualified">
          <xsd:element name="Request">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="arg1" type="xsd:string"/>
                <xsd:element name="arg2" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
      </types>

      <message name="Input">
        <part element="tns:Request"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="literal"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    serialized = operation.input.serialize(arg1='ah1', arg2='ah2')
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:ns0="http://tests.python-zeep.org/tns"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <soap-env:Body>
            <ns0:Request>
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:Request>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_serialize_with_header():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema targetNamespace="http://tests.python-zeep.org/tns"
                    elementFormDefault="qualified">
          <xsd:element name="Request">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="arg1" type="xsd:string"/>
                <xsd:element name="arg2" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
          <xsd:element name="Authentication">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="username" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
      </types>

      <message name="Input">
        <part element="tns:Request"/>
        <part element="tns:Authentication" name="Header"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="literal"/>
            <soap:header message="tns:Input" part="Header" use="literal"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    serialized = operation.input.serialize(
        arg1='ah1', arg2='ah2',
        _soapheaders={'Authentication': {'username': 'mvantellingen'}})
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:ns0="http://tests.python-zeep.org/tns"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <soap-env:Header>
            <ns0:Authentication>
              <ns0:username>mvantellingen</ns0:username>
            </ns0:Authentication>
          </soap-env:Header>
          <soap-env:Body>
            <ns0:Request>
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:Request>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_serialize_with_headers_simple():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema targetNamespace="http://tests.python-zeep.org/tns"
                    elementFormDefault="qualified">
          <xsd:element name="Request">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="arg1" type="xsd:string"/>
                <xsd:element name="arg2" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
          <xsd:element name="Authentication">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="username" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
      </types>

      <message name="Input">
        <part element="tns:Request"/>
        <part element="tns:Authentication" name="Header"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="literal"/>
            <soap:header message="tns:Input" part="Header" use="literal"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    header = xsd.Element(None, xsd.ComplexType(
        xsd.Sequence([
            xsd.Element('{http://www.w3.org/2005/08/addressing}Action', xsd.String()),
            xsd.Element('{http://www.w3.org/2005/08/addressing}To', xsd.String()),
        ])
    ))
    header_value = header(Action='doehet', To='server')
    serialized = operation.input.serialize(
        arg1='ah1', arg2='ah2',
        _soapheaders=[header_value])
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:ns0="http://tests.python-zeep.org/tns"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <soap-env:Header>
            <ns1:Action xmlns:ns1="http://www.w3.org/2005/08/addressing">doehet</ns1:Action>
            <ns2:To xmlns:ns2="http://www.w3.org/2005/08/addressing">server</ns2:To>
          </soap-env:Header>
          <soap-env:Body>
            <ns0:Request>
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:Request>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_serialize_with_header_and_custom_mixed():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema targetNamespace="http://tests.python-zeep.org/tns"
                    elementFormDefault="qualified">
          <xsd:element name="Request">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="arg1" type="xsd:string"/>
                <xsd:element name="arg2" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
          <xsd:element name="Authentication">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="username" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
      </types>

      <message name="Input">
        <part element="tns:Request"/>
        <part element="tns:Authentication" name="Header"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="literal"/>
            <soap:header message="tns:Input" part="Header" use="literal"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    header = root.types.get_element(
        '{http://tests.python-zeep.org/tns}Authentication'
    )
    header_1 = header(username='mvantellingen')

    header = xsd.Element(
        '{http://test.python-zeep.org/custom}custom',
        xsd.ComplexType([
            xsd.Element('{http://test.python-zeep.org/custom}foo', xsd.String()),
        ])
    )
    header_2 = header(foo='bar')

    serialized = operation.input.serialize(
        arg1='ah1', arg2='ah2',
        _soapheaders=[header_1, header_2])
    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:ns0="http://tests.python-zeep.org/tns"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <soap-env:Header>
            <ns0:Authentication>
              <ns0:username>mvantellingen</ns0:username>
            </ns0:Authentication>
            <ns1:custom xmlns:ns1="http://test.python-zeep.org/custom">
              <ns1:foo>bar</ns1:foo>
            </ns1:custom>
          </soap-env:Header>
          <soap-env:Body>
            <ns0:Request>
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:Request>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_serializer_with_header_custom_elm():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema targetNamespace="http://tests.python-zeep.org/tns"
                    elementFormDefault="qualified">
          <xsd:element name="Request">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="arg1" type="xsd:string"/>
                <xsd:element name="arg2" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
      </types>

      <message name="Input">
        <part element="tns:Request"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="literal"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    header = xsd.Element(
        '{http://test.python-zeep.org/custom}auth',
        xsd.ComplexType([
            xsd.Element('{http://test.python-zeep.org/custom}username', xsd.String()),
        ])
    )

    serialized = operation.input.serialize(
        arg1='ah1', arg2='ah2', _soapheaders=[header(username='mvantellingen')])

    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:ns0="http://tests.python-zeep.org/tns"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <soap-env:Header>
            <ns1:auth xmlns:ns1="http://test.python-zeep.org/custom">
              <ns1:username>mvantellingen</ns1:username>
            </ns1:auth>
          </soap-env:Header>
          <soap-env:Body>
            <ns0:Request>
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:Request>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_serializer_with_header_custom_xml():
    wsdl_content = StringIO("""
    <definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
                 xmlns:tns="http://tests.python-zeep.org/tns"
                 xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 targetNamespace="http://tests.python-zeep.org/tns">
      <types>
        <xsd:schema targetNamespace="http://tests.python-zeep.org/tns"
                    elementFormDefault="qualified">
          <xsd:element name="Request">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="arg1" type="xsd:string"/>
                <xsd:element name="arg2" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
      </types>

      <message name="Input">
        <part element="tns:Request"/>
      </message>

      <portType name="TestPortType">
        <operation name="TestOperation">
          <input message="Input"/>
        </operation>
      </portType>

      <binding name="TestBinding" type="tns:TestPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="TestOperation">
          <soap:operation soapAction=""/>
          <input>
            <soap:body use="literal"/>
          </input>
        </operation>
      </binding>
    </definitions>
    """.strip())

    root = wsdl.Document(wsdl_content, None)

    binding = root.bindings['{http://tests.python-zeep.org/tns}TestBinding']
    operation = binding.get('TestOperation')

    header_value = etree.Element('{http://test.python-zeep.org/custom}auth')
    etree.SubElement(
        header_value, '{http://test.python-zeep.org/custom}username'
    ).text = 'mvantellingen'

    serialized = operation.input.serialize(
        arg1='ah1', arg2='ah2', _soapheaders=[header_value])

    expected = """
        <?xml version="1.0"?>
        <soap-env:Envelope
            xmlns:ns0="http://tests.python-zeep.org/tns"
            xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
          <soap-env:Header>
            <ns0:auth xmlns:ns0="http://test.python-zeep.org/custom">
              <ns0:username>mvantellingen</ns0:username>
            </ns0:auth>
          </soap-env:Header>
          <soap-env:Body>
            <ns0:Request>
              <ns0:arg1>ah1</ns0:arg1>
              <ns0:arg2>ah2</ns0:arg2>
            </ns0:Request>
          </soap-env:Body>
        </soap-env:Envelope>
    """
    assert_nodes_equal(expected, serialized.content)


def test_deserialize():
    response_body = load_xml("""
        <SOAP-ENV:Body
            xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <mns:response xmlns:mns="http://test.python-zeep.org/tests/document"
                SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <mns:return type="xsd:string">foobar</mns:return>
          </mns:response>
        </SOAP-ENV:Body>
    """)  # noqa
    wsdl = stub(types=stub(_prefix_map={}))
    operation = stub(soapaction='my-action', name='something')

    msg = messages.DocumentMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
        nsmap=soap.Soap11Binding.nsmap,
        type='input')

    # Fake resolve()
    namespace = 'http://test.python-zeep.org/tests/document'
    msg.abstract = definitions.AbstractMessage(
        etree.QName(namespace, 'Method1Response'))
    msg.abstract.parts = OrderedDict([
        ('body', definitions.MessagePart(
            element=xsd.Element(
                etree.QName(namespace, 'response'),
                xsd.ComplexType([
                    xsd.Element(etree.QName(namespace, 'return'), xsd.String()),
                ])
            ),
            type=None))
        ])

    msg.namespace = {
        'body': 'http://test.python-zeep.org/tests/document',
        'header': None,
        'headerfault': None
    }

    result = msg.deserialize(response_body)
    assert result == 'foobar'


def test_deserialize_choice():
    response_body = load_xml("""
        <SOAP-ENV:Body
            xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <mns:response xmlns:mns="http://test.python-zeep.org/tests/document"
                SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <mns:return type="xsd:string">foobar</mns:return>
          </mns:response>
        </SOAP-ENV:Body>
    """)  # noqa
    wsdl = stub(types=stub(_prefix_map={}))
    operation = stub(soapaction='my-action', name='something')

    msg = messages.DocumentMessage(
        wsdl=wsdl,
        name=None,
        operation=operation,
        nsmap=soap.Soap11Binding.nsmap,
        type='input')

    # Fake resolve()
    namespace = 'http://test.python-zeep.org/tests/document'
    msg.abstract = definitions.AbstractMessage(
        etree.QName(namespace, 'Method1Response'))
    msg.abstract.parts = OrderedDict([
        ('body', definitions.MessagePart(
            element=xsd.Element(
                etree.QName(namespace, 'response'),
                xsd.ComplexType(
                    xsd.Choice([
                        xsd.Element(etree.QName(namespace, 'return'), xsd.String()),
                    ])
                )
            ),
            type=None))
        ])

    msg.namespace = {
        'body': 'http://test.python-zeep.org/tests/document',
        'header': None,
        'headerfault': None
    }

    result = msg.deserialize(response_body)
    assert result == 'foobar'
