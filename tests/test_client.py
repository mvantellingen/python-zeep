import pytest
import requests_mock

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


def test_service_proxy():
    client_obj = client.Client('tests/wsdl_files/soap.wsdl')

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
        result = client_obj.service.GetLastTradePrice('foobar')
        assert result.price == 120.123


def test_call_method():
    obj = client.Client('tests/wsdl_files/soap.wsdl')

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
        result = obj.call(
            '{http://example.com/stockquote.wsdl}GetLastTradePrice',
            tickerSymbol='foobar'
        )
        assert result.price == 120.123


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
            result = obj.call(
                '{http://example.com/stockquote.wsdl}GetLastTradePrice',
                tickerSymbol='foobar'
            )
