# -*- coding: utf-8 -*-
"""
======================================================
Test_mtom_attachment :mod:`tests.test_mtom_attachment`
======================================================

"""
import os
from os.path import join, basename
import tempfile
import shutil
import email
import hashlib
from lxml import etree
import pytest
import requests_mock
from zeep import client
from zeep import ns
from zeep import transport_with_attach as twa
TMP_DIR = tempfile.gettempdir()
TMP_OUT = join(TMP_DIR, 'mtom_test', 'out')
TMP_IN = join(TMP_DIR, 'mtom_test', 'in')
MB = 2**20
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

CLIENT = client.Client(
    'tests/wsdl_files/mtom_attachment.wsdl', transport=twa.TransportWithAttach())


@pytest.mark.requests
def create_service():
    """Create service"""
    return CLIENT.create_service(
        '{http://test.ellethee.org/}MtomAttachmentBinding',
        'http://test.python-zeep.org/x')


def create_random_file(filename, size=1024):
    """Create random file"""
    with open(filename, 'wb') as fout:
        fout.write(os.urandom(size))


def get_parts(string):
    """get parts"""
    msg = twa.get_multipart()
    msg.set_payload(string)
    msg = email.message_from_string(msg.as_string())
    parts = []
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        cid = part.get("Content-ID").strip("<>")
        if cid:
            item = {
                'cid': cid,
                'cte': part.get("Content-Transfer-Encoding"),
            }
            if item['cte'] == 'binary':
                item['payload'] = join(TMP_IN, cid[twa.ID_LEN + 1:])
                with open(item['payload'], 'wb') as fobj:
                    fobj.write(part.get_payload())
            else:
                item['payload'] = part.get_payload()
            parts.append(item)
    return parts


def create_tmp_dirs():
    """create_tmp_dirs"""
    try:
        os.makedirs(TMP_OUT)
    except OSError:
        pass
    try:
        os.makedirs(TMP_IN)
    except OSError:
        pass


def remove_tmp_dirs():
    """removes tmp dirs"""
    shutil.rmtree(TMP_OUT)
    shutil.rmtree(TMP_IN)


def get_file_md5(filename, blocksize=2**20):
    """get file md5"""
    md5 = hashlib.md5()
    with open(filename, "rb") as fin:
        while True:
            buf = fin.read(blocksize)
            if not buf:
                break
            md5.update(buf)
    return md5.hexdigest()


def test_multi_upload():
    """Test multiUpload"""
    service = create_service()
    create_tmp_dirs()
    files = [1, 2, 3, 10]
    for idx, size in enumerate(files):
        filename = join(TMP_OUT, 'test_file_{}'.format(idx))
        create_random_file(filename, size * MB)
        files[idx] = {'fileName': basename(filename),
                      "fileBytes": CLIENT.attach(filename)}
    with requests_mock.mock() as rmock:
        rmock.post('http://test.python-zeep.org/x', text=RESPONSE)
        result = service.multiUpload(files)
        assert result == "ok"
        parts = get_parts(rmock.request_history[0].body)
        xml = etree.fromstring(parts[0]['payload'])
        items = xml.findall(".//{http://test.ellethee.org/}arrayOfUpload/item")
        for item in items:
            filename = item.find("fileName").text
            assert get_file_md5(
                join(TMP_IN, filename)) == get_file_md5(join(TMP_OUT, filename))
        remove_tmp_dirs()


def test_upload():
    """Test Upload"""
    service = create_service()
    create_tmp_dirs()
    filename = join(TMP_OUT, 'test_file')
    create_random_file(filename, 15 * MB)
    with requests_mock.mock() as rmock:
        rmock.post('http://test.python-zeep.org/x', text=RESPONSE)
        result = service.upload(basename(filename), CLIENT.attach(filename))
        assert result == "ok"
        parts = get_parts(rmock.request_history[0].body)
        xml = etree.fromstring(parts[0]['payload'])
        items = xml.findall(".//{http://test.ellethee.org/}arrayOfUpload/item")
        for item in items:
            filename = item.find("fileName").text
            assert get_file_md5(
                join(TMP_IN, filename)) == get_file_md5(join(TMP_OUT, filename))
        remove_tmp_dirs()
