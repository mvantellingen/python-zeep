# -*- coding: utf-8 -*-
"""
==================================
Utils :mod:`transport_with_attach`
==================================
Utils to add basic MTOMS attachment

author: ellethee <luca800@gmail.com>
based on http://stackoverflow.com/questions/35558812/how-to-send-multipart-related-requests-in-python-to-soap-server

This works for me.
"""
from os.path import basename
import random
import string
from email.mime.application import MIMEApplication
from email.encoders import encode_7or8bit
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from base64 import b64decode, b64encode
from lxml import etree
from zeep.transports import Transport
from zeep.wsdl.utils import etree_to_string
from zeep.xsd import builtins
from zeep.wsdl.bindings import http
from zeep.wsdl import wsdl
import zeep.ns
from zeep import client
BOUND = "MTOM".center(40, "=")
# XOP_LINK = "http://www.w3.org/2004/08/xop/include"
FILETAG = 'xop:Include:'
ID_LEN = 16
func_getid = lambda N: ''.join(
    random.SystemRandom().choice(string.ascii_uppercase + string.digits)
    for _ in range(N))

# I need it my WSDL uses it for the data part.
def xmlvalue(self, value):
    """Patch for xmlvalue"""
    if value.startswith(FILETAG):
        return value
    return b64encode(value)

def pythonvalue(self, value):
    """Patch for pythonvalue"""
    if value.startswith(FILETAG):
        return value
    return b64decode(value)

def patch_things():
    """Patches something"""
    # Let's patch the Base64Binary data type.
    builtins.Base64Binary.accepted_types += (etree.Element, )
    builtins.Base64Binary.xmlvalue = xmlvalue
    builtins.Base64Binary.pythonvalue = pythonvalue
    # Base64Binary patched.
    # Update NSMAP
    zeep.ns.XOP = "http://www.w3.org/2004/08/xop/include"
    zeep.ns.XMIME5 = "http://www.w3.org/2005/05/xmlmime"
    # attach method for the client.
    zeep.Client.attach = _client_attach

def set_attachnode(node):
    """Set the attachment node"""
    cid = node.text[len(FILETAG):]
    node.text = None
    etree.SubElement(
        node, '{{{}}}Include'.format(zeep.ns.XOP), href="cid:{}".format(cid))
    return cid

def get_multipart():
    """Get the main multipart object"""
    part = MIMEMultipart(
        'related', charset='utf-8', type='application/xop+xml',
        boundary=BOUND, start='<soap-env:Envelope>')
    part.set_param('start-info', 'application/soap+xml')
    return part

def get_envelopepart(envelope):
    """The Envelope part"""
    part = MIMEApplication(etree_to_string(envelope), 'xop+xml', encode_7or8bit)
    part.set_param('charset', 'utf-8')
    part.set_param('type', 'application/soap+xml')
    part.add_header('Content-ID', '<soap-env:Envelope>')
    part.add_header('Content-Transfer-Encoding', 'binary')
    return part

def _client_attach(self, filename):
    """add attachment"""
    attach = Attachment(filename)
    self.transport.attachments[attach.cid] = attach
    return attach.tag


class Attachment(object):
    """Attachment class"""
    def __init__(self, filename):
        self.filename = filename
        self.basename = basename(self.filename)
        self.cid = func_getid(ID_LEN) + ":" + self.basename
        self.tag = FILETAG + self.cid


class TransportWithAttach(Transport):
    """Transport with attachment"""

    def __init__(self, cache=None, timeout=300, operation_timeout=None,
                 session=None):
        self.attachments = {}
        patch_things()
        super(TransportWithAttach, self).__init__(
            cache=cache, timeout=timeout, operation_timeout=operation_timeout,
            session=session)

    def post_xml(self, address, envelope, headers):
        # Search for values that startswith FILETAG
        filetags = envelope.xpath(
            "//*[starts-with(text(), '{}')]".format(FILETAG))
        # if there is some attached file we set the attachments
        if filetags:
            message = self.set_attachs(filetags, envelope, headers)
        # else just the envelope
        else:
            message = etree_to_string(envelope)
        # post the data.
        return self.post(address, message, headers)

    def set_attachs(self, filetags, envelope, headers):
        """Set mtom attachs and return the right envelope"""
        # let's get the mtom multi part.
        mtom_part = get_multipart()
        # let's set xop:Include for al the files.
        # we need to do this before get the envelope part.
        files = [set_attachnode(f) for f in filetags]
        # get the envelope part.
        env_part = get_envelopepart(envelope)
        # attach the env_part to the multipart.
        mtom_part.attach(env_part)
        # for each filename in files.
        for cid in files:
            # attach the filepart to the multipart.
            mtom_part.attach(self.get_attachpart(cid))
        # some other stuff.
        bound = '--{}'.format(mtom_part.get_boundary())
        marray = mtom_part.as_string().split(bound)
        mtombody = bound
        mtombody += bound.join(marray[1:])
        mtom_part.add_header("Content-Length", str(len(mtombody)))
        headers.update(dict(mtom_part.items()))
        message = mtom_part.as_string().split('\n\n', 1)[1]
        message = message.replace('\n', '\r\n', 5)
        # return the messag for the post.
        return message

    def get_attachpart(self, cid):
        """The file part"""
        attach = self.attachments[cid]
        part = MIMEBase("*", "*")
        part['Content-Transfer-Encoding'] = "binary"
        part['Content-ID'] = "<{}>".format(attach.cid)
        part.set_payload(open(attach.filename, 'rb').read())
        del part['mime-version']
        return part
