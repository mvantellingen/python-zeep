import os
import sys

import pytest
import zeep
from zeep.wsse.signature import xmlsec as xmlsec_installed
import requests_mock
from zeep.wsse.signature import Signature
from zeep import helpers


KEY_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "cert_valid.pem")
PUBLIC_CERT_TO_VERIFY_RESP = os.path.join(os.path.dirname(os.path.realpath(__file__)), "public_cert_to_verify_response.crt")
WSDL_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "wsdl_files/wsdl_to_verify_response.wsdl")
RESPONSE_XML = os.path.join(os.path.dirname(os.path.realpath(__file__)), "responses_examples/response_signed.xml")

skip_if_no_xmlsec = pytest.mark.skipif(
    sys.platform == "win32", reason="does not run on windows"
) and pytest.mark.skipif(
    xmlsec_installed is None, reason="xmlsec library not installed"
)


@skip_if_no_xmlsec
def test_wsse_verify_response():
    """
    1 - We assume that the answer from any server from any company is signed.
    2 - We have a public certificate of any company to verify signed responses.
    """
    sig = Signature(key_file=KEY_FILE, certfile=KEY_FILE, cert_public_to_verify_response=PUBLIC_CERT_TO_VERIFY_RESP)
    client = zeep.Client(wsdl=WSDL_FILE, wsse=sig)
    response_ = open(RESPONSE_XML, "r")
    response = response_.read()
    with requests_mock.mock() as m:
        m.post('https://webservice.face.gob.es', text=response, status_code=200)
        result = client.service.consultarFactura('2022-000566048')
        resp_exp = {"resultado": {"codigo": "0", "descripcion": "Correcto/Zuzena", "codigoSeguimiento": None}, "factura": {"numeroRegistro": "2022-000566048", "tramitacion": {"codigo": "1200", "descripcion": "Erregistratua / Registrada", "motivo": None}, "anulacion": {"codigo": "4100", "descripcion": "Ezeztapena ez da eskatu / No solicita anulación", "motivo": None}}}
        resp = helpers.serialize_object(result, dict)
        assert resp_exp == resp