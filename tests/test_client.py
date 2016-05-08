import pytest
import requests_mock

from zeep import client


def test_bind():
    client_obj = client.Client('tests/wsdl_files/soap.wsdl')
    service = client_obj.bind()
    assert service


def test_bind_service():
    client_obj = client.Client('tests/wsdl_files/soap.wsdl')
    service = client_obj.bind('StockQuoteService')
    assert service


def test_bind_service_port():
    client_obj = client.Client('tests/wsdl_files/soap.wsdl')
    service = client_obj.bind('StockQuoteService', 'StockQuotePort')
    assert service


@pytest.mark.requests
def test_service_proxy():
    client_obj = client.Client('tests/wsdl_files/soap.wsdl')

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
        result = client_obj.service.GetLastTradePrice('foobar')
        assert result == 120.123


@pytest.mark.requests
def test_call_method_fault():
    obj = client.Client('tests/wsdl_files/soap.wsdl')

    response = """
        <?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope
            xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <soap:Body>
            <soap:Fault>
              <faultcode>soap:Server</faultcode>
              <faultstring>
                Big fatal error!!
              </faultstring>
              <faultactor>StockListByDate</faultactor>
              <detail>
                <Error xmlns="http://sherpa.sherpaan.nl/Sherpa">
                  <ErrorMessage>wrong security code</ErrorMessage>
                  <ErrorSource>StockListByDate</ErrorSource>
                </Error>
              </detail>
            </soap:Fault>
          </soap:Body>
        </soap:Envelope>
    """.strip()

    with requests_mock.mock() as m:
        m.post('http://example.com/stockquote', text=response, status_code=500)
        with pytest.raises(IOError):
            obj.service.GetLastTradePrice(tickerSymbol='foobar')
