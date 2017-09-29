import os
import sys

import pytest

from tests.utils import load_xml
from zeep import wsse
from zeep.exceptions import SignatureVerificationFailed
from zeep.wsse import signature

DS_NS = 'http://www.w3.org/2000/09/xmldsig#'


KEY_FILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'cert_valid.pem')
KEY_FILE_PW = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'cert_valid_pw.pem')


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="does not run on windows")
def test_sign():
    envelope = load_xml("""
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
    """)

    signature.sign_envelope(envelope, KEY_FILE, KEY_FILE)
    signature.verify_envelope(envelope, KEY_FILE)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="does not run on windows")
def test_sign_pw():
    envelope = load_xml("""
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
    """)

    signature.sign_envelope(envelope, KEY_FILE_PW, KEY_FILE_PW, 'geheim')
    signature.verify_envelope(envelope, KEY_FILE_PW)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="does not run on windows")
def test_verify_error():
    envelope = load_xml("""
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
    """)

    signature.sign_envelope(envelope, KEY_FILE, KEY_FILE)
    nsmap = {'tns': 'http://tests.python-zeep.org/'}

    for elm in envelope.xpath('//tns:Argument', namespaces=nsmap):
        elm.text = 'NOT!'

    with pytest.raises(SignatureVerificationFailed):
        signature.verify_envelope(envelope, KEY_FILE)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="does not run on windows")
def test_signature():
    envelope = load_xml("""
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
    """)

    plugin = wsse.Signature(KEY_FILE_PW, KEY_FILE_PW, 'geheim')
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)
