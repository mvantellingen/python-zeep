from zeep import wsdl
from zeep.transports import Transport
import requests_mock


def test_parse_wsdl():
    obj = wsdl.WSDL('tests/wsdl_files/soap.wsdl')
    assert len(obj.services) == 1

    service = obj.services['{http://example.com/stockquote.wsdl}StockQuoteService']
    assert service
    assert len(service.ports) == 1

    port = service.ports['{http://example.com/stockquote.wsdl}StockQuotePort']
    assert port

    transport = Transport()

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
