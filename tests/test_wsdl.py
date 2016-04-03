import pytest
import requests_mock

from tests.utils import assert_nodes_equal
from zeep import wsdl
from zeep.transports import Transport


@pytest.fixture()
def wsdl_obj():

    class DummyWSDL(wsdl.WSDL):
        def __init__(self):
            self.schema_references = {}
            self.transport = None

    return DummyWSDL()


def test_parse_soap_wsdl():
    transport = Transport()

    obj = wsdl.WSDL('tests/wsdl_files/soap.wsdl', transport=transport)
    assert len(obj.services) == 1

    service = obj.services['{http://example.com/stockquote.wsdl}StockQuoteService']
    assert service
    assert len(service.ports) == 1

    port = service.ports['{http://example.com/stockquote.wsdl}StockQuotePort']
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
        result = port.send(
            transport=transport,
            operation='{http://example.com/stockquote.wsdl}GetLastTradePrice',
            args=[],
            kwargs={'tickerSymbol': 'foobar'})
        assert result == 120.123

        request = m.request_history[0]

        # Compare request body
        expected = """
        <soap-env:Envelope
                xmlns:ns0="http://example.com/stockquote.xsd"
                xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema">
           <soap-env:Body>
              <ns0:TradePriceRequest>
                 <tickerSymbol>foobar</tickerSymbol>
              </ns0:TradePriceRequest>
           </soap-env:Body>
        </soap-env:Envelope>
        """
        assert_nodes_equal(expected, request.body)


def test_parse_soap_header_wsdl():
    transport = Transport()

    obj = wsdl.WSDL('tests/wsdl_files/soap_header.wsdl', transport=transport)
    assert len(obj.services) == 1

    service = obj.services['{http://example.com/stockquote.wsdl}StockQuoteService']
    assert service
    assert len(service.ports) == 1

    port = service.ports['{http://example.com/stockquote.wsdl}StockQuotePort']
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
        result = port.send(
            transport=transport,
            operation='{http://example.com/stockquote.wsdl}GetLastTradePrice',
            args=[],
            kwargs={
                'tickerSymbol': 'foobar',
                '_soapheader': {
                    'username': 'ikke',
                    'password': 'oeh-is-geheim!',
                }
            })

        assert result == 120.123

        request = m.request_history[0]

        # Compare request body
        expected = """
        <soap-env:Envelope
                xmlns:ns0="http://example.com/stockquote.xsd"
                xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema">
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


def test_parse_types_multiple_schemas(wsdl_obj):

    node = wsdl_obj._parse_content(b"""
    <?xml version="1.0" encoding="utf-8"?>
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

    assert wsdl_obj.parse_types(node)


def test_parse_types_nsmap_issues(wsdl_obj):
    node = wsdl_obj._parse_content(b"""
    <?xml version="1.0" encoding="UTF-8"?>
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

    assert wsdl_obj.parse_types(node)
