# -*- coding: utf-8 -*-
"""
======================================================
Test_mtom_attachment :mod:`tests.test_mtom_attachment`
======================================================

"""
import pytest
import requests_mock

from zeep import client
from zeep.transport_with_attach import TransportWithAttach, attach
from zeep.exceptions import Error
from tests.utils import load_xml

RESPONSE = b"""
<?xml version="1.0"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:exam="http://example.com/">
   <soapenv:Header/>
   <soapenv:Body>
      <exam:uploadResponse>
         <message>ok</message>
      </exam:uploadResponse>
   </soapenv:Body>
</soapenv:Envelope>""".strip()


@pytest.mark.requests
def test_create_service():
    client_obj = client.Client(
        'tests/wsdl_files/mtom_attachment.wsdl',
        transport=TransportWithAttach())
    service = client_obj.create_service(
        '{http://example.com/}MtomAttachmentBinding',
        'http://test.python-zeep.org/x')

    with requests_mock.mock() as m:
        m.post('http://test.python-zeep.org/x', text=RESPONSE)
        result = service.upload([
            {'fileName': "testfile.txt", "fileBytes": attach("tests/testfile.txt")},
            {'fileName': "testfile.txt", "fileBytes": attach("tests/testfile.txt")},
            {'fileName': "testfile.txt", "fileBytes": attach("tests/testfile.txt")},
            {'fileName': "testfile.txt", "fileBytes": attach("tests/testfile.txt")},
        ])
        assert result == "ok"
        assert m.request_history[0].headers['User-Agent'].startswith('Zeep/')
        print  m.request_history[0].body
        assert False
        # assert m.request_history[0].body.startswith(
        #     b"<?xml version='1.0' encoding='utf-8'?>")
