import datetime
import os
import sys

import pytest
import requests_mock
from freezegun import freeze_time

from tests.utils import assert_nodes_equal, load_xml
from zeep import client
from zeep.wsse import UsernameToken
from zeep.wsse import Signature
from zeep.wsse import signature
from lxml.etree import tostring


KEY_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'cert_valid.pem')
KEY_FILE_PW = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'cert_valid_pw.pem')


@pytest.mark.requests
def test_integration():

    envelope = load_xml("""
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
    """)

    
    client_obj=client.Client(
        'tests/wsdl_files/soap.wsdl',
        wsse =[UsernameToken('username', 'password'), Signature(KEY_FILE_PW, KEY_FILE_PW, 'geheim')])

    response="""
    <?xml version="1.0"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:stoc="http://example.com/stockquote.xsd">
        <soapenv:Header>
            <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
                <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
                    <SignedInfo>
                        <CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                        <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
                        <Reference URI="#id-54c21059-f045-441c-8118-9581b9a37637">
                            <Transforms>
                                <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </Transforms>
                            <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                            <DigestValue>LpksGAS1L7t8GdabCKPHOC3zMiQ=</DigestValue>
                        </Reference>
                        <Reference URI="#id-168e043d-15c1-4975-b750-3194c57bf302">
                            <Transforms>
                                <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                            </Transforms>
                            <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                            <DigestValue>npLJVhdpDNVTeVCdSO+FjmPvKOQ=</DigestValue>
                        </Reference>
                    </SignedInfo>
                    <SignatureValue>wARsz0pankjgxDPZwbt3VUHrwUxe49GpGtXLsZdNO7O+AlzFzeeLgQeitB4mDwtpYPovr6GYTPIfaSs09JfHA6CcSNfIgWbUNxFjhcZP1lvba2CtKutEBzDMmhungr9QUeEjNBkV+w+bpnJ1vCKDDy8T9f5B3boIxoeY8gE44FNxb8Nw5KKJKOwI0iMCFnS279QoAOHgDV1w1mACm/CmAs8qwpCjceboMLED1faaPH2QPslBV0RzsefwoO+bWV1FH/U7GGpcjwSGjB13wdfk7B6WpM3O0fIegjBpRPNf9EEuO5+KpG5RPcgjjfk+nGcm5veAyDJuKs5bZ7KDoSAg4g==</SignatureValue>
                    <KeyInfo>
                        <wsse:SecurityTokenReference>
                            <X509Data>
                                <X509IssuerSerial>
                                    <X509IssuerName>emailAddress=info@python-zeep.org,CN=www.python-zeep.org,O=Michael van Tellingen,L=Utrecht,ST=Utrecht,C=NL</X509IssuerName>
                                    <X509SerialNumber>12934907582145619385</X509SerialNumber>
                                </X509IssuerSerial>
                                <X509Certificate>MIIEqjCCA5KgAwIBAgIJALOCBen0S+W5MA0GCSqGSIb3DQEBBQUAMIGUMQswCQYDVQQGEwJOTDEQMA4GA1UECBMHVXRyZWNodDEQMA4GA1UEBxMHVXRyZWNodDEeMBwGA1UEChMVTWljaGFlbCB2YW4gVGVsbGluZ2VuMRwwGgYDVQQDExN3d3cucHl0aG9uLXplZXAub3JnMSMwIQYJKoZIhvcNAQkBFhRpbmZvQHB5dGhvbi16ZWVwLm9yZzAeFw0xNzAxMjUxOTI3NTJaFw0yNzAxMjMxOTI3NTJaMIGUMQswCQYDVQQGEwJOTDEQMA4GA1UECBMHVXRyZWNodDEQMA4GA1UEBxMHVXRyZWNodDEeMBwGA1UEChMVTWljaGFlbCB2YW4gVGVsbGluZ2VuMRwwGgYDVQQDExN3d3cucHl0aG9uLXplZXAub3JnMSMwIQYJKoZIhvcNAQkBFhRpbmZvQHB5dGhvbi16ZWVwLm9yZzCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMq1sZUbZwE+6tiIFhGkFAsBvtIDbqkzT1It3y2f+1yO5TgXpk092HgmXO320y6wAR/JeDRHVxufAhWvzJHbJtOV7eBt2r62E/gjWQN7Tn+Nk7BiAef1b6nfS0uLoQVKNqqnE1M9VQPIz+wimNuXavESxHdYMN5S4zxqmGuvbFJBGMwAQriXz/cVBMki3nJcVsfpMtj6fAAFz6Q7ZRnW/a7M8WIUibXHvyhLG2amgkPWtmQCXhWriYlLzgzzYoLPL1ECxjWB3JhJuEr1ZEkoL6SnpAJNYAudTqi2MqafHPdep9QxtjwuW/ZE4+plF5AaGvY41iUGJBPMxucG2jO8QBsCAwEAAaOB/DCB+TAdBgNVHQ4EFgQUxd12m9nIS0QO4uIPRy7oerPyVygwgckGA1UdIwSBwTCBvoAUxd12m9nIS0QO4uIPRy7oerPyVyihgZqkgZcwgZQxCzAJBgNVBAYTAk5MMRAwDgYDVQQIEwdVdHJlY2h0MRAwDgYDVQQHEwdVdHJlY2h0MR4wHAYDVQQKExVNaWNoYWVsIHZhbiBUZWxsaW5nZW4xHDAaBgNVBAMTE3d3dy5weXRob24temVlcC5vcmcxIzAhBgkqhkiG9w0BCQEWFGluZm9AcHl0aG9uLXplZXAub3JnggkAs4IF6fRL5bkwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQUFAAOCAQEAHTUp/i9FYbvl86By7EvMlZeKv6I38IYcrIGzDdbrk8KkilYv7p2Ll8gUJYRFj96iX6Uvn0ACTutFJW9xE2ytBMOuUurTBpcpk8k368gfO/fGVi6HzjyFqTnhLkmd3CADIzPN/yg5j2q+mgA3ys6wISBRaDJR2jGt9sTAkAwkVJdDCFkCwyRfB28mBRnI5SLeR5vQyLT97THPma39xR3FaqYvh2q3coXBnaOOcuigiKyIynhJtXH42XlN3TM23b9NK2Oep2e51pxst3uohlDGmB/Wuzx/hG+kNxy9D+Ms7qNL9+i4nHFOoR034RB/NGTChzTxq2JcXIKPWIo2tslNsg==</X509Certificate>
                            </X509Data>
                        </wsse:SecurityTokenReference>
                    </KeyInfo>
                </Signature>
                <ns0:Timestamp xmlns:ns0="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" ns0:Id="id-168e043d-15c1-4975-b750-3194c57bf302"/>
            </wsse:Security>
        </soapenv:Header>
        <soapenv:Body xmlns:ns0="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" ns0:Id="id-54c21059-f045-441c-8118-9581b9a37637">
            <stoc:TradePrice>
                <price>120.123</price>
            </stoc:TradePrice>
        </soapenv:Body>
    </soapenv:Envelope>
    """.strip()

    with requests_mock.mock() as m:
        m.post('http://example.com/stockquote', text = response)
        result=client_obj.service.GetLastTradePrice('foobar')
        assert result == 120.123