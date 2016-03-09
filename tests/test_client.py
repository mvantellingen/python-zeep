from zeep import client


def test_get_port_default():
    client_obj = client.Client('tests/wsdl_files/soap.wsdl')
    port = client_obj.get_port()
    assert port


def test_get_port_service():
    client_obj = client.Client('tests/wsdl_files/soap.wsdl')
    port = client_obj.get_port('StockQuoteService')
    assert port


def test_get_port_service_port():
    client_obj = client.Client('tests/wsdl_files/soap.wsdl')
    port = client_obj.get_port('StockQuoteService', 'StockQuotePort')
    assert port
