from zeep import wsdl


def test_parse_wsdl():
    obj = wsdl.WSDL('tests/wsdl_files/soap.wsdl')
    assert len(obj.services) == 1

    service = obj.services['{http://example.com/stockquote.wsdl}StockQuoteService']
    assert service
    assert len(service.ports) == 1

    port = service.ports['{http://example.com/stockquote.wsdl}StockQuotePort']
    assert port

    operation = port.get_operation('{http://example.com/stockquote.wsdl}GetLastTradePrice')
    assert operation
    assert operation.input
    assert operation.output
