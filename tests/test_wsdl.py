import io

import pytest
import requests_mock
from lxml import etree
from pretend import stub
from six import StringIO

from tests.utils import DummyTransport, assert_nodes_equal
from zeep import wsdl
from zeep.transports import Transport


@pytest.mark.requests
def test_parse_soap_wsdl():
    client = stub(transport=Transport(), wsse=None)

    obj = wsdl.Document('tests/wsdl_files/soap.wsdl', transport=client.transport)
    assert len(obj.services) == 1

    service = obj.services['StockQuoteService']
    assert service
    assert len(service.ports) == 1

    port = service.ports['StockQuotePort']
    assert port

    response = """
        <?xml version="1.0"?>
        <soapenv:Envelope
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:stoc="http://example.com/stockquote.xsd">
           <soapenv:Header/>
           <soapenv:Body>
              <stoc:TradePrice>
                 <price>120.123</price>
              </stoc:TradePrice>
           </soapenv:Body>
        </soapenv:Envelope>
    """.strip()

    with requests_mock.mock() as m:
        m.post('http://example.com/stockquote', text=response)
        account_type = obj.types.get_type('{http://example.com/stockquote.xsd}account')
        account = account_type(id=100)
        country = obj.types.get_element(
            '{http://example.com/stockquote.xsd}country'
        ).type()
        country.name = 'The Netherlands'
        country.code = 'NL'
        result = port.binding.send(
            client=client,
            options={'address': 'http://example.com/stockquote'},
            operation='GetLastTradePrice',
            args=[],
            kwargs={'tickerSymbol': 'foobar', 'account': account, 'country': country})
        assert result == 120.123

        request = m.request_history[0]

        # Compare request body
        expected = """
        <soap-env:Envelope
                xmlns:ns0="http://example.com/stockquote.xsd"
                xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
            <soap-env:Body>
              <ns0:TradePriceRequest>
                <tickerSymbol>foobar</tickerSymbol>
                <account>
                  <id>100</id>
                  <user/>
                </account>
                <ns0:country>
                  <name>The Netherlands</name>
                  <code>NL</code>
                </ns0:country>
              </ns0:TradePriceRequest>
           </soap-env:Body>
        </soap-env:Envelope>
        """
        assert_nodes_equal(expected, request.body)


@pytest.mark.requests
def test_parse_soap_header_wsdl():
    client = stub(transport=Transport(), wsse=None)

    obj = wsdl.Document(
        'tests/wsdl_files/soap_header.wsdl', transport=client.transport)
    assert len(obj.services) == 1

    service = obj.services['StockQuoteService']
    assert service
    assert len(service.ports) == 1

    port = service.ports['StockQuotePort']
    assert port

    response = """
    <?xml version="1.0"?>
    <soapenv:Envelope
        xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:stoc="http://example.com/stockquote.xsd">
       <soapenv:Header/>
       <soapenv:Body>
          <stoc:TradePrice>
             <price>120.123</price>
          </stoc:TradePrice>
       </soapenv:Body>
    </soapenv:Envelope>
    """.strip()

    with requests_mock.mock() as m:
        m.post('http://example.com/stockquote', text=response)
        result = port.binding.send(
            client=client,
            options={'address': 'http://example.com/stockquote'},
            operation='GetLastTradePrice',
            args=[],
            kwargs={
                'tickerSymbol': 'foobar',
                '_soapheaders': {
                    'Authentication': {
                        'username': 'ikke',
                        'password': 'oeh-is-geheim!',
                    }
                }
            })

        assert result == 120.123

        request = m.request_history[0]

        # Compare request body
        expected = """
        <soap-env:Envelope
                xmlns:ns0="http://example.com/stockquote.xsd"
                xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
           <soap-env:Header>
              <ns0:Authentication>
                 <username>ikke</username>
                 <password>oeh-is-geheim!</password>
              </ns0:Authentication>
           </soap-env:Header>
           <soap-env:Body>
              <ns0:TradePriceRequest>
                 <tickerSymbol>foobar</tickerSymbol>
              </ns0:TradePriceRequest>
           </soap-env:Body>
        </soap-env:Envelope>
        """
        assert_nodes_equal(expected, request.body)


def test_parse_types_multiple_schemas():

    content = StringIO("""
    <?xml version="1.0"?>
    <wsdl:definitions xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:s1="http://microsoft.com/wsdl/types/"
        xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
        xmlns:tns="http://tests.python-zeep.org/"
        xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
        targetNamespace="http://tests.python-zeep.org/">
      <wsdl:types>
        <xsd:schema elementFormDefault="qualified"
            xmlns:s1="http://microsoft.com/wsdl/types/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:tns="http://tests.python-zeep.org//"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="http://tests.python-zeep.org/">
          <xsd:import namespace="http://microsoft.com/wsdl/types/" />
          <xsd:element name="foobardiedar" type="s1:guid"/>
        </xsd:schema>
        <xsd:schema elementFormDefault="qualified"
           targetNamespace="http://microsoft.com/wsdl/types/">
          <xsd:simpleType name="guid">
            <xsd:restriction base="xsd:string"/>
          </xsd:simpleType>
        </xsd:schema>
      </wsdl:types>
    </wsdl:definitions>
    """.strip())

    assert wsdl.Document(content, None)


def test_parse_types_nsmap_issues():
    content = StringIO("""
    <?xml version="1.0"?>
    <wsdl:definitions targetNamespace="urn:ec.europa.eu:taxud:vies:services:checkVat"
      xmlns:tns1="urn:ec.europa.eu:taxud:vies:services:checkVat:types"
      xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/"
      xmlns:impl="urn:ec.europa.eu:taxud:vies:services:checkVat"
      xmlns:apachesoap="http://xml.apache.org/xml-soap"
      xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
      xmlns:xsd="http://www.w3.org/2001/XMLSchema"
      xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/">
      <wsdl:types>
        <xsd:schema attributeFormDefault="qualified"
            elementFormDefault="qualified"
            targetNamespace="urn:ec.europa.eu:taxud:vies:services:checkVat:types"
            xmlns="urn:ec.europa.eu:taxud:vies:services:checkVat:types">
                <xsd:element name="checkVatApprox">
                    <xsd:complexType>
                        <xsd:sequence>
                            <xsd:element maxOccurs="1" minOccurs="0"
                                name="traderCompanyType"
                                type="tns1:companyTypeCode"/>
                        </xsd:sequence>
                    </xsd:complexType>
                </xsd:element>
                <xsd:simpleType name="companyTypeCode">
                    <xsd:restriction base="xsd:string">
                        <xsd:pattern value="[A-Z]{2}\-[1-9][0-9]?"/>
                    </xsd:restriction>
                </xsd:simpleType>
            </xsd:schema>
      </wsdl:types>
    </wsdl:definitions>
    """.strip())
    assert wsdl.Document(content, None)


@pytest.mark.requests
def test_parse_soap_import_wsdl():
    client = stub(transport=Transport(), wsse=None)
    content = io.open(
        'tests/wsdl_files/soap-enc.xsd', 'r', encoding='utf-8').read()

    with requests_mock.mock() as m:
        m.get('http://schemas.xmlsoap.org/soap/encoding/', text=content)

        obj = wsdl.Document(
            'tests/wsdl_files/soap_import_main.wsdl', transport=client.transport)
        assert len(obj.services) == 1
        assert obj.types.is_empty is False
        obj.dump()


def test_multiple_extension():
    content = StringIO("""
    <?xml version="1.0"?>
    <wsdl:definitions
      xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
      xmlns:xsd="http://www.w3.org/2001/XMLSchema"
      xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/">
      <wsdl:types>
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
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/c"
            targetNamespace="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:complexType name="type_c">
              <xs:complexContent>
                <xs:extension base="tns:type_d"/>
              </xs:complexContent>
            </xs:complexType>

            <xs:complexType name="type_d">
                <xs:attribute name="wat" type="xs:string" />
            </xs:complexType>
        </xs:schema>
      </wsdl:types>
    </wsdl:definitions>
    """.strip())
    document = wsdl.Document(content, None)

    type_a = document.types.get_type('ns1:type_a')
    type_a(wat='x')


def test_create_import_schema(recwarn):
    content = StringIO("""
    <?xml version="1.0"?>
    <wsdl:definitions
      xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
      xmlns:xsd="http://www.w3.org/2001/XMLSchema"
      xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/">

      <wsdl:types>
        <xsd:schema>
          <xsd:import namespace="http://tests.python-zeep.org/a"
                      schemaLocation="a.xsd"/>
        </xsd:schema>
        <xsd:schema>
          <xsd:import namespace="http://tests.python-zeep.org/b"
                      schemaLocation="b.xsd"/>
        </xsd:schema>
      </wsdl:types>
    </wsdl:definitions>
    """.strip())

    schema_node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">
        </xsd:schema>
    """.strip())

    schema_node_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            targetNamespace="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

            <xsd:element name="global" type="xsd:string"/>
        </xsd:schema>
    """.strip())

    transport = DummyTransport()
    transport.bind('a.xsd', schema_node_a)
    transport.bind('b.xsd', schema_node_b)

    document = wsdl.Document(content, transport)
    assert len(recwarn) == 0
    assert document.types.get_element('{http://tests.python-zeep.org/b}global')


def test_wsdl_import(recwarn):
    wsdl_main = StringIO("""
        <?xml version="1.0"?>
        <wsdl:definitions
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:tns="http://tests.python-zeep.org/xsd-main"
          xmlns:sec="http://tests.python-zeep.org/wsdl-secondary"
          xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
          xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/"
          targetNamespace="http://tests.python-zeep.org/xsd-main">
          <wsdl:import namespace="http://tests.python-zeep.org/wsdl-secondary"
            location="http://tests.python-zeep.org/schema-2.wsdl"/>
          <wsdl:types>
            <xsd:schema
                targetNamespace="http://tests.python-zeep.org/xsd-main"
                xmlns:tns="http://tests.python-zeep.org/xsd-main">
              <xsd:element name="input" type="xsd:string"/>
            </xsd:schema>
          </wsdl:types>
          <wsdl:message name="message-1">
            <wsdl:part name="response" element="tns:input"/>
          </wsdl:message>

          <wsdl:portType name="TestPortType">
            <wsdl:operation name="TestOperation1">
              <wsdl:input message="message-1"/>
            </wsdl:operation>
            <wsdl:operation name="TestOperation2">
              <wsdl:input message="sec:message-2"/>
            </wsdl:operation>
          </wsdl:portType>

          <wsdl:binding name="TestBinding" type="tns:TestPortType">
            <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
            <wsdl:operation name="TestOperation1">
              <soap:operation soapAction=""/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
            </wsdl:operation>
            <wsdl:operation name="TestOperation2">
              <soap:operation soapAction=""/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
            </wsdl:operation>
          </wsdl:binding>
          <wsdl:service name="TestService">
            <wsdl:documentation>Test service</wsdl:documentation>
            <wsdl:port name="TestPortType" binding="tns:TestBinding">
              <soap:address location="http://tests.python-zeep.org/test"/>
            </wsdl:port>
          </wsdl:service>
        </wsdl:definitions>
    """.strip())

    wsdl_2 = ("""
        <?xml version="1.0"?>
        <wsdl:definitions
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:tns="http://tests.python-zeep.org/wsdl-secondary"
          xmlns:mine="http://tests.python-zeep.org/xsd-secondary"
          xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/"
          targetNamespace="http://tests.python-zeep.org/wsdl-secondary">
          <wsdl:types>
            <xsd:schema
                targetNamespace="http://tests.python-zeep.org/xsd-secondary"
                xmlns:tns="http://tests.python-zeep.org/xsd-secondary">
              <xsd:element name="input2" type="xsd:string"/>
            </xsd:schema>
          </wsdl:types>
          <wsdl:message name="message-2">
            <wsdl:part name="response" element="mine:input2"/>
          </wsdl:message>
        </wsdl:definitions>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/schema-2.wsdl', wsdl_2)
    document = wsdl.Document(wsdl_main, transport)
    document.dump()


def test_wsdl_import_transitive(recwarn):
    wsdl_main = StringIO("""
        <?xml version="1.0"?>
        <wsdl:definitions
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:tns="http://tests.python-zeep.org/xsd-main"
          xmlns:sec="http://tests.python-zeep.org/wsdl-2"
          xmlns:third="http://tests.python-zeep.org/wsdl-3"
          xmlns:fourth="http://tests.python-zeep.org/wsdl-4"
          xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
          xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/"
          targetNamespace="http://tests.python-zeep.org/xsd-main">
          <wsdl:import namespace="http://tests.python-zeep.org/wsdl-2"
            location="http://tests.python-zeep.org/schema-2.wsdl"/>
          <wsdl:types>
            <xsd:schema
                targetNamespace="http://tests.python-zeep.org/xsd-main"
                xmlns:tns="http://tests.python-zeep.org/xsd-main">
              <xsd:element name="input" type="xsd:string"/>
            </xsd:schema>
          </wsdl:types>
          <wsdl:message name="message-1">
            <wsdl:part name="response" element="tns:input"/>
          </wsdl:message>

          <wsdl:portType name="TestPortType">
            <wsdl:operation name="TestOperation1">
              <wsdl:input message="message-1"/>
            </wsdl:operation>
            <wsdl:operation name="TestOperation2">
              <wsdl:input message="sec:message-2"/>
            </wsdl:operation>
            <wsdl:operation name="TestOperation3">
              <wsdl:input message="third:message-3"/>
            </wsdl:operation>
            <wsdl:operation name="TestOperation4">
              <wsdl:input message="fourth:message-4"/>
            </wsdl:operation>
          </wsdl:portType>

          <wsdl:binding name="TestBinding" type="tns:TestPortType">
            <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
            <wsdl:operation name="TestOperation1">
              <soap:operation soapAction=""/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
            </wsdl:operation>
            <wsdl:operation name="TestOperation2">
              <soap:operation soapAction=""/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
            </wsdl:operation>
            <wsdl:operation name="TestOperation3">
              <soap:operation soapAction=""/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
            </wsdl:operation>
          </wsdl:binding>
          <wsdl:service name="TestService">
            <wsdl:documentation>Test service</wsdl:documentation>
            <wsdl:port name="TestPortType" binding="tns:TestBinding">
              <soap:address location="http://tests.python-zeep.org/test"/>
            </wsdl:port>
          </wsdl:service>
        </wsdl:definitions>
    """.strip())

    wsdl_2 = ("""
        <?xml version="1.0"?>
        <wsdl:definitions
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:tns="http://tests.python-zeep.org/wsdl-2"
          xmlns:mine="http://tests.python-zeep.org/xsd-2"
          xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/"
          targetNamespace="http://tests.python-zeep.org/wsdl-2">
          <wsdl:import namespace="http://tests.python-zeep.org/wsdl-3"
            location="http://tests.python-zeep.org/schema-3.wsdl"/>
          <wsdl:types>
            <xsd:schema
                targetNamespace="http://tests.python-zeep.org/xsd-2"
                xmlns:tns="http://tests.python-zeep.org/xsd-2">
              <xsd:element name="input2" type="xsd:string"/>
            </xsd:schema>
          </wsdl:types>
          <wsdl:message name="message-2">
            <wsdl:part name="response" element="mine:input2"/>
          </wsdl:message>
        </wsdl:definitions>
    """.strip())

    wsdl_3 = ("""
        <?xml version="1.0"?>
        <wsdl:definitions
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:tns="http://tests.python-zeep.org/wsdl-third"
          xmlns:mine="http://tests.python-zeep.org/xsd-3"
          xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/"
          targetNamespace="http://tests.python-zeep.org/wsdl-3">
          <wsdl:import namespace="http://tests.python-zeep.org/wsdl-2"
            location="http://tests.python-zeep.org/schema-2.wsdl"/>
          <wsdl:import namespace="http://tests.python-zeep.org/wsdl-4"
            location="http://tests.python-zeep.org/schema-4.wsdl"/>
          <wsdl:types>
            <xsd:schema
                targetNamespace="http://tests.python-zeep.org/xsd-3"
                xmlns:tns="http://tests.python-zeep.org/xsd-3">
              <xsd:element name="input3" type="xsd:string"/>
            </xsd:schema>
          </wsdl:types>
          <wsdl:message name="message-3">
            <wsdl:part name="response" element="mine:input3"/>
          </wsdl:message>
        </wsdl:definitions>
    """.strip())

    wsdl_4 = ("""
        <?xml version="1.0"?>
        <wsdl:definitions
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:tns="http://tests.python-zeep.org/wsdl-4"
          xmlns:mine="http://tests.python-zeep.org/xsd-4"
          xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/"
          targetNamespace="http://tests.python-zeep.org/wsdl-4">
          <wsdl:import namespace="http://tests.python-zeep.org/wsdl-3"
            location="http://tests.python-zeep.org/schema-3.wsdl"/>
          <wsdl:message name="message-4">
            <wsdl:part name="response" type="xsd:string"/>
          </wsdl:message>
        </wsdl:definitions>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/schema-2.wsdl', wsdl_2)
    transport.bind('http://tests.python-zeep.org/schema-3.wsdl', wsdl_3)
    transport.bind('http://tests.python-zeep.org/schema-4.wsdl', wsdl_4)

    document = wsdl.Document(wsdl_main, transport)
    document.dump()


def test_wsdl_import_xsd_references(recwarn):
    wsdl_main = StringIO("""
        <?xml version="1.0"?>
        <wsdl:definitions
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:tns="http://tests.python-zeep.org/xsd-main"
          xmlns:sec="http://tests.python-zeep.org/wsdl-secondary"
          xmlns:xsd-sec="http://tests.python-zeep.org/xsd-secondary"
          xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
          xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/"
          targetNamespace="http://tests.python-zeep.org/xsd-main">
          <wsdl:import namespace="http://tests.python-zeep.org/wsdl-secondary"
            location="http://tests.python-zeep.org/schema-2.wsdl"/>
          <wsdl:types>
            <xsd:schema
                targetNamespace="http://tests.python-zeep.org/xsd-main"
                xmlns:tns="http://tests.python-zeep.org/xsd-main">
              <xsd:element name="input" type="xsd:string"/>
            </xsd:schema>
          </wsdl:types>
          <wsdl:message name="message-1">
            <wsdl:part name="response" element="tns:input"/>
          </wsdl:message>
          <wsdl:message name="message-2">
            <wsdl:part name="response" element="xsd-sec:input2"/>
          </wsdl:message>

          <wsdl:portType name="TestPortType">
            <wsdl:operation name="TestOperation1">
              <wsdl:input message="message-1"/>
            </wsdl:operation>
            <wsdl:operation name="TestOperation2">
              <wsdl:input message="sec:message-2"/>
            </wsdl:operation>
          </wsdl:portType>

          <wsdl:binding name="TestBinding" type="tns:TestPortType">
            <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
            <wsdl:operation name="TestOperation1">
              <soap:operation soapAction=""/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
            </wsdl:operation>
            <wsdl:operation name="TestOperation2">
              <soap:operation soapAction=""/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
            </wsdl:operation>
          </wsdl:binding>
          <wsdl:service name="TestService">
            <wsdl:documentation>Test service</wsdl:documentation>
            <wsdl:port name="TestPortType" binding="tns:TestBinding">
              <soap:address location="http://tests.python-zeep.org/test"/>
            </wsdl:port>
          </wsdl:service>
        </wsdl:definitions>
    """.strip())

    wsdl_2 = ("""
        <?xml version="1.0"?>
        <wsdl:definitions
          xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          xmlns:tns="http://tests.python-zeep.org/wsdl-secondary"
          xmlns:mine="http://tests.python-zeep.org/xsd-secondary"
          xmlns:wsdlsoap="http://schemas.xmlsoap.org/wsdl/soap/"
          targetNamespace="http://tests.python-zeep.org/wsdl-secondary">
          <wsdl:types>
            <xsd:schema
                targetNamespace="http://tests.python-zeep.org/xsd-secondary"
                xmlns:tns="http://tests.python-zeep.org/xsd-secondary">
              <xsd:element name="input2" type="xsd:string"/>
            </xsd:schema>
          </wsdl:types>
          <wsdl:message name="message-2">
            <wsdl:part name="response" element="mine:input2"/>
          </wsdl:message>
        </wsdl:definitions>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/schema-2.wsdl', wsdl_2)
    document = wsdl.Document(wsdl_main, transport)
    document.dump()
