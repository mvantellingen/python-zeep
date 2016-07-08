import io

import pytest
import requests_mock
from pretend import stub
from six import StringIO

from tests.utils import assert_nodes_equal
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
        account = obj.types.get_type('{http://example.com/stockquote.xsd}account')
        account.id = 100
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
