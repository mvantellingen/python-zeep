
import pytest
import requests_mock
from zeep import Client
from zeep.transports import Transport

transport = Transport()
client = Client('tests/wsdl_files/claim.wsdl', transport=transport)

data = "\r\n".join("""
--MIME_boundary
Content-Type: text/xml; charset=UTF-8
Content-Transfer-Encoding: 8bit
Content-ID: <claim061400a.xml@claiming-it.com>

<?xml version='1.0' ?>
<SOAP-ENV:Envelope
xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
<SOAP-ENV:Body>
<claim:insurance_claim_auto id="insurance_claim_document_id"
xmlns:claim="http://schemas.risky-stuff.com/Auto-Claim">
<theSignedForm href="cid:claim061400a.tiff@claiming-it.com"/>
<theCrashPhoto href="cid:claim061400a.jpeg@claiming-it.com"/>
<!-- ... more claim details go here... -->
</claim:insurance_claim_auto>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>

--MIME_boundary
Content-Type: image/tiff
Content-Transfer-Encoding: base64
Content-ID: <claim061400a.tiff@claiming-it.com>

...Base64 encoded TIFF image...
--MIME_boundary
Content-Type: image/jpeg
Content-Transfer-Encoding: binary
Content-ID: <claim061400a.jpeg@claiming-it.com>

...Raw JPEG image..
--MIME_boundary--

""".splitlines()).encode('utf-8')

@pytest.mark.requests
def test_multipart():
    with requests_mock.Mocker() as m:
        m.post('https://www.risky-stuff.com/claim.svc',
               headers= {'Content-Type': 'multipart/related; type="text/xml"; start="<claim061400a.xml@claiming-it.com>"; boundary="MIME_boundary"'},
               content=data
               )
        parts = client.service.GetClaimDetails('061400a')

        assert parts[0].headers['Content-ID'] == "<claim061400a.xml@claiming-it.com>"
        assert parts[1].headers['Content-ID'] == "<claim061400a.tiff@claiming-it.com>"
        assert parts[2].headers['Content-ID'] == "<claim061400a.jpeg@claiming-it.com>"
