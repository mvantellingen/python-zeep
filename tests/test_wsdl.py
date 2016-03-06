from zeep import wsdl
from zeep.transports import Transport


def test_parse_wsdl():
    obj = wsdl.WSDL('tests/wsdl_files/soap.wsdl')
    assert len(obj.services) == 1

    service = obj.services['{http://example.com/stockquote.wsdl}StockQuoteService']
    assert service
    assert len(service.ports) == 1

    port = service.ports['{http://example.com/stockquote.wsdl}StockQuotePort']
    assert port

    transport = Transport()

    port.send(
        transport=transport,
        operation='{http://example.com/stockquote.wsdl}GetLastTradePrice',
        args=[],
        kwargs={'tickerSymbol': 'foobar'})


    # print operation.input('John', 'Doe', 'j.doe@example.com')
