import os
import sys

import pytest
from lxml.etree import QName

from tests.utils import load_xml
from zeep import ns, wsse
from zeep.exceptions import SignatureVerificationFailed
from zeep.wsse import signature
from zeep.wsse.signature import xmlsec as xmlsec_installed

DS_NS = "http://www.w3.org/2000/09/xmldsig#"


KEY_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "cert_valid.pem")
KEY_FILE_PW = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "cert_valid_pw.pem"
)


skip_if_no_xmlsec = pytest.mark.skipif(
    sys.platform == "win32", reason="does not run on windows"
) and pytest.mark.skipif(
    xmlsec_installed is None, reason="xmlsec library not installed"
)


@skip_if_no_xmlsec
def test_sign_timestamp_if_present():
    envelope = load_xml(
        """
        <soapenv:Envelope
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
            xmlns:wsu="http://schemas.xmlsoap.org/ws/2003/06/utility">
          <soapenv:Header>
            <wsu:Timestamp>
              <wsu:Created>2018-11-18T15:44:27Z</wsu:Created>
              <wsu:Expires>2018-11-18T15:54:27Z</wsu:Expires>
            </wsu:Timestamp>
          </soapenv:Header>
          <soapenv:Body>
            <tns:Function>
              <tns:Argument>OK</tns:Argument>
            </tns:Function>
          </soapenv:Body>
        </soapenv:Envelope>
    """
    )

    signature.sign_envelope(envelope, KEY_FILE, KEY_FILE)
    signature.verify_envelope(envelope, KEY_FILE)

@skip_if_no_xmlsec
def test_sign():
    envelope = load_xml(
        """
        <soapenv:Envelope
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
          <soapenv:Header></soapenv:Header>
          <soapenv:Body>
            <tns:Function>
              <tns:Argument>OK</tns:Argument>
            </tns:Function>
          </soapenv:Body>
        </soapenv:Envelope>
    """
    )

    signature.sign_envelope(envelope, KEY_FILE, KEY_FILE)
    signature.verify_envelope(envelope, KEY_FILE)


@skip_if_no_xmlsec
def test_sign_pw():
    envelope = load_xml(
        """
        <soapenv:Envelope
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
          <soapenv:Header></soapenv:Header>
          <soapenv:Body>
            <tns:Function>
              <tns:Argument>OK</tns:Argument>
            </tns:Function>
          </soapenv:Body>
        </soapenv:Envelope>
    """
    )

    signature.sign_envelope(envelope, KEY_FILE_PW, KEY_FILE_PW, "geheim")
    signature.verify_envelope(envelope, KEY_FILE_PW)


@skip_if_no_xmlsec
def test_verify_error():
    envelope = load_xml(
        """
        <soapenv:Envelope
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
          <soapenv:Header></soapenv:Header>
          <soapenv:Body>
            <tns:Function>
              <tns:Argument>OK</tns:Argument>
            </tns:Function>
          </soapenv:Body>
        </soapenv:Envelope>
    """
    )

    signature.sign_envelope(envelope, KEY_FILE, KEY_FILE)
    nsmap = {"tns": "http://tests.python-zeep.org/"}

    for elm in envelope.xpath("//tns:Argument", namespaces=nsmap):
        elm.text = "NOT!"

    with pytest.raises(SignatureVerificationFailed):
        signature.verify_envelope(envelope, KEY_FILE)


@skip_if_no_xmlsec
def test_signature():
    envelope = load_xml(
        """
        <soapenv:Envelope
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
          <soapenv:Header></soapenv:Header>
          <soapenv:Body>
            <tns:Function>
              <tns:Argument>OK</tns:Argument>
            </tns:Function>
          </soapenv:Body>
        </soapenv:Envelope>
    """
    )

    plugin = wsse.Signature(KEY_FILE_PW, KEY_FILE_PW, "geheim")
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
def test_signature_binary():
    envelope = load_xml(
        """
        <soapenv:Envelope
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
          <soapenv:Header></soapenv:Header>
          <soapenv:Body>
            <tns:Function>
              <tns:Argument>OK</tns:Argument>
            </tns:Function>
          </soapenv:Body>
        </soapenv:Envelope>
    """
    )

    plugin = wsse.BinarySignature(KEY_FILE_PW, KEY_FILE_PW, "geheim")
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)
    # Test the reference
    bintok = envelope.xpath(
        "soapenv:Header/wsse:Security/wsse:BinarySecurityToken",
        namespaces={"soapenv": ns.SOAP_ENV_11, "wsse": ns.WSSE},
    )[0]
    ref = envelope.xpath(
        "soapenv:Header/wsse:Security/ds:Signature/ds:KeyInfo/wsse:SecurityTokenReference"
        "/wsse:Reference",
        namespaces={"soapenv": ns.SOAP_ENV_11, "wsse": ns.WSSE, "ds": ns.DS},
    )[0]
    assert "#" + bintok.attrib[QName(ns.WSU, "Id")] == ref.attrib["URI"]
