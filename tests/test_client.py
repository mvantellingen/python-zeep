from zeep import client


def test_create_soap_message():
    soap = client.create_soap_message()
