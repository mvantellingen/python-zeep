import os.path

import pytest
import requests_mock
from lxml import etree

from zeep import client
from zeep.wsse import binsectoken

KEY_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'x509.pem')


@pytest.fixture
def xml():
    return etree.fromstring("""
    <soapenv:Envelope xmlns:zeep="http://tests.python-zeep.org/binsectoken"
        xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
        xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
      <soapenv:Body>
        <zeep:Function>
          <zeep:Argument>OK</zeep:Argument>
        </zeep:Function>
      </soapenv:Body>
    </soapenv:Envelope>
    """.strip())


@pytest.fixture
def xml_signed():
    return etree.fromstring("""
<soapenv:Envelope xmlns:mvt="http://github.com/mvantellingen"
                    xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
                    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
   <soapenv:Header>
      <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
         <wsse:BinarySecurityToken wsu:Id="id-e173afc8-2e7f-4d37-9ef5-160b84e210ab" EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3">MIIEgzCCA2ugAwIBAgIJAMkiZttOMvKxMA0GCSqGSIb3DQEBBQUAMIGHMQswCQYDVQQGEwJOTDETMBEGA1UECBMKR2VsZGVybGFuZDEMMAoGA1UEBxMDRWRlMRAwDgYDVQQKEwdMdWtraWVuMRgwFgYDVQQDEw9wb24ubHVra2llbi5jb20xKTAnBgkqhkiG9w0BCQEWGm0udmFudGVsbGluZ2VuQGx1a2tpZW4uY29tMB4XDTE1MDEyOTE2MDk0OVoXDTE3MTAyNTE2MDk0OVowgYcxCzAJBgNVBAYTAk5MMRMwEQYDVQQIEwpHZWxkZXJsYW5kMQwwCgYDVQQHEwNFZGUxEDAOBgNVBAoTB0x1a2tpZW4xGDAWBgNVBAMTD3Bvbi5sdWtraWVuLmNvbTEpMCcGCSqGSIb3DQEJARYabS52YW50ZWxsaW5nZW5AbHVra2llbi5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDC/R9s5eApMoc+B9G9IklGtcjkOAftHmntTrbKGACz9dTRIURCeqtuJuEvvvpAarnFftIb39tAvdrwkZIkmaAUowcD7OHsOJlsojNY7vYxju8Clx45XJ9HcvL6EkHpd2lRuLx9dSfwTfGKtnTaFhJt8ZnLjNSbWK/5IHHvrv/gYtDKhahK6ncBW2k5nXZf6Wn2Rn/RpjkSoQL12Gmyh47EXMvbA9HpxxqDlPWBBNp6hpGhGOkg0EVvRgnKwzkqvTyB6571LsNMVe7U+gkmd9GHxx8t3cloWLG9RSD/Qr0ahQpFPI00c4dHN0a1LG4WCzbFN8mZYr3WSqsx1OUY1eHJAgMBAAGjge8wgewwHQYDVR0OBBYEFKicd7yRgkGBJJoO/s49iSF3N91CMIG8BgNVHSMEgbQwgbGAFKicd7yRgkGBJJoO/s49iSF3N91CoYGNpIGKMIGHMQswCQYDVQQGEwJOTDETMBEGA1UECBMKR2VsZGVybGFuZDEMMAoGA1UEBxMDRWRlMRAwDgYDVQQKEwdMdWtraWVuMRgwFgYDVQQDEw9wb24ubHVra2llbi5jb20xKTAnBgkqhkiG9w0BCQEWGm0udmFudGVsbGluZ2VuQGx1a2tpZW4uY29tggkAySJm204y8rEwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQUFAAOCAQEAo43YKvwGepefY3mazx+PUa5OCozHHNtvpZpXRtN/3bwggXZdJqTyJjmlEQBZz/yAyJL5Ar8FtMenR4Ki8E9Esn09L/l2rA0JvLP8IMBZHfqdDM2Za5zJwp541y4jRjcNlVJ57bwby3DlBp8u70wrtGp8PNC1cGLr9Wj61mERjQAeIn4Qv8JBKiuvQ+YiHN5x1baOCxOWYGFlukXiGDcnNse0BC144yBJraoLzCI6VQYSws1n33VyjPPySpDeR2/JdS6ZO1E/yhuqqwXt8p3g3i7brkpxbQYYeBQA0idDBO7bVQOBoXYGbIN2AIrkPnm4zkki1kivh5NP4PakO6TPDQ==</wsse:BinarySecurityToken>
         <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
            <SignedInfo>
               <CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
               <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
               <Reference URI="#id-b88aa1ed-1b06-4b40-b110-5c239a6b5ce3">
                  <Transforms>
                     <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#">
                        <ec:InclusiveNamespaces PrefixList="urn" xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#"/>
                     </Transform>
                  </Transforms>
                  <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
                  <DigestValue>NRPhamBfgxgTWPf6+8Xzga+YMtg=</DigestValue>
               </Reference>
            </SignedInfo>
            <SignatureValue>ms8rrvFl12PTyhZFBBI6l5T9wCCljGamaiVzGS3HcTGw+gQ5YwHSPSuwAAxhSXKi
krHVN0zEw6p0HZC5RJR/XFrCLPScsrDQOjIP2pKU3uuKR7wFLFDzygS5yU7qpuSn
TdoRuqyOgT5lgvDlDBXn534cQHW3yOUVUl3u+QWdrDtVehag17JBDA89db5KiOfW
ReaTUxHjYmYJaEtY4HLr9PGvtS4pEpr+FCvHoq0aKI40BqyGar4G1/8tavWGaFV0
vMSZrBGvRxqq6Gotjjt47LhlYq3JvpLLLi+SOjF5388LMKZ+gLLapIY0OhvnGEvl
JvsAu49CHgPAlLdF3wvIgA==</SignatureValue>
            <KeyInfo>
               <wsse:SecurityTokenReference wsse:TokenType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3">
                  <wsse:Reference ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" URI="#id-e173afc8-2e7f-4d37-9ef5-160b84e210ab"/>
               </wsse:SecurityTokenReference>
            </KeyInfo>
         </Signature>
      </wsse:Security>
   </soapenv:Header>
   <soapenv:Body ns0:Id="id-b88aa1ed-1b06-4b40-b110-5c239a6b5ce3" xmlns:ns0="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
      <mvt:Function>
         <mvt:Argument>OK</mvt:Argument>
      </mvt:Function>
   </soapenv:Body>
</soapenv:Envelope>
""".strip())  # noqa


def test_wsse_sign(xml):
    auth = binsectoken.BinarySecurityToken(KEY_FILE)
    envelope, headers = auth.sign(xml, {})
    auth.verify(envelope)


def test_wsse_verify(xml_signed):
    auth = binsectoken.BinarySecurityToken(KEY_FILE)
    with pytest.raises(binsectoken.CertificationError):
        auth.verify(xml_signed)


def test_wsse_verify_unsigned(xml):
    auth = binsectoken.BinarySecurityToken(KEY_FILE)
    with pytest.raises(binsectoken.CertificationError):
        auth.verify(xml)


def test_sign_roundtrip(xml):
    signed = binsectoken.sign_envelope(xml, KEY_FILE)
    result = binsectoken.verify_envelope(signed, KEY_FILE)
    assert result is True


def test_sign_roundtrip_failed(xml):
    signed = binsectoken.sign_envelope(xml, KEY_FILE)
    node = signed.find('.//{http://tests.python-zeep.org/binsectoken}Argument')
    node.text = 'NOT OK!'
    result = binsectoken.verify_envelope(signed, KEY_FILE)
    assert result is False


@pytest.mark.requests
def test_integration():
    client_obj = client.Client(
        'tests/wsdl_files/soap.wsdl',
        wsse=binsectoken.BinarySecurityToken(KEY_FILE))

    xml = etree.fromstring("""
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
    """.strip())
    signed = binsectoken.sign_envelope(xml, KEY_FILE)
    response = etree.tostring(signed)

    with requests_mock.mock() as m:
        m.post('http://example.com/stockquote', text=response)
        client_obj.service.GetLastTradePrice('foobar')
        request = m.request_history[0]

        assert 'SecurityTokenReference' in request.body
