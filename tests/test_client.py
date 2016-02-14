from zeep import client


def test_call_func():
    soap = client.Client('tests/wsdl_files/sample.wsdl')
    soap.call('GetLastTradePrice')


def test_create_soap_message():
    soap = client.create_soap_message()

    from lxml import etree

    print etree.tostring(soap)
