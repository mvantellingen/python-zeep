import requests_mock

from tests.utils import assert_nodes_equal
from zeep import wsdl
from zeep.transports import Transport


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
    <SOAP-ENV:Envelope
      xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
      xmlns:s="http://example.com/stockquote.xsd">
      <SOAP-ENV:Body>
        <s:TradePrice>
          <s:price>120.123</s:price>
        </s:TradePrice>
      </SOAP-ENV:Body>
    </SOAP-ENV:Envelope>
    """.strip()

    with requests_mock.mock() as m:
        m.post('http://example.com/stockquote', text=response)
        result = port.send(
            transport=transport,
            operation='{http://example.com/stockquote.wsdl}GetLastTradePrice',
            args=[],
            kwargs={'tickerSymbol': 'foobar'})
        assert result.price == 120.123

        request = m.request_history[0]

        # Compare request body
        expected = """
            <soap-env:Envelope
                xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:soap12="http://schemas.xmlsoap.org/wsdl/soap12/"
                xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            >
              <soap-env:Body>
                <TradePriceRequest xmlns="http://example.com/stockquote.xsd">
                  <tickerSymbol>foobar</tickerSymbol>
                </TradePriceRequest>
              </soap-env:Body>
            </soap-env:Envelope>
        """
        assert_nodes_equal(expected, request.body)


def test_parse_soap_header_wsdl():
    transport = Transport()

    obj = wsdl.WSDL('tests/wsdl_files/soap_header.wsdl', transport=transport)
    obj.dump()
    return
    assert len(obj.services) == 1

    service = obj.services['{http://example.com/stockquote.wsdl}StockQuoteService']
    assert service
    assert len(service.ports) == 1

    port = service.ports['{http://example.com/stockquote.wsdl}StockQuotePort']
    assert port

    response = b"""
    <?xml version="1.0"?>
    <SOAP-ENV:Envelope
      xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
      xmlns:s="http://example.com/stockquote.xsd">
      <SOAP-ENV:Body>
        <s:TradePrice>
          <s:price>120.123</s:price>
        </s:TradePrice>
      </SOAP-ENV:Body>
    </SOAP-ENV:Envelope>
    """.strip()

    with requests_mock.mock() as m:
        m.post('http://example.com/stockquote', text=response)
        result = port.send(
            transport=transport,
            operation='{http://example.com/stockquote.wsdl}GetLastTradePrice',
            args=[],
            kwargs={'tickerSymbol': 'foobar'})
        assert result.price == 120.123

        request = m.request_history[0]

        # Compare request body
        expected = b"""
            <soap-env:Envelope
                xmlns:http="http://schemas.xmlsoap.org/wsdl/http/"
                xmlns:mime="http://schemas.xmlsoap.org/wsdl/mime/"
                xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
                xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:soap12="http://schemas.xmlsoap.org/wsdl/soap12/"
                xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            >
              <soap-env:Body>
                <TradePriceRequest xmlns="http://example.com/stockquote.xsd">
                  <tickerSymbol>foobar</tickerSymbol>
                </TradePriceRequest>
              </soap-env:Body>
            </soap-env:Envelope>
        """
        assert_nodes_equal(expected, request.body)
