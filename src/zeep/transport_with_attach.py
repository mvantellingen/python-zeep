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
import zeep.ns
BOUND = "MTOM".center(40, "=")
XOP_LINK = "http://www.w3.org/2004/08/xop/include"
FILETAG = 'xop:Include:'

# Let's patch the Base64Binary data type.
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

builtins.Base64Binary.accepted_types += (etree.Element, )
builtins.Base64Binary.xmlvalue = xmlvalue
builtins.Base64Binary.pythonvalue = pythonvalue
# Base64Binary patched.
# Update NSMAP
zeep.ns.xop = "http://www.w3.org/2004/08/xop/include"
zeep.ns.xmime5 = "http://www.w3.org/2005/05/xmlmime"
http.NSMAP.update({
    "xop": zeep.ns.xop,
    "xmime5": zeep.ns.xmime5
})

def attach(filename):
    """Returns the placeholder for the file."""
    return FILETAG + filename

def set_attachnode(node):
    """Set the attachment node"""
    filename = node.text[len(FILETAG):]
    node.text = None
    etree.SubElement(
        node, '{{{}}}Include'.format(XOP_LINK), href="cid:{}".format(filename))
    return filename

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

def get_attachpart(filename):
    """The file part"""
    part = MIMEBase("*", "*")
    part['Content-Transfer-Encoding'] = "binary"
    part['Content-ID'] = "<{}>".format(filename)
    part.set_payload(open(filename, 'rb').read())
    del part['mime-version']
    return part

def set_attachs(filetags, envelope, headers):
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
    for filename in files:
        # attach the filepart to the multipart.
        mtom_part.attach(get_attachpart(filename))
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


class TransportWithAttach(Transport):
    """Transport with attachment"""

    def post_xml(self, address, envelope, headers):
        # Search for values that startswith FILETAG
        filetags = envelope.xpath(
            "//*[starts-with(text(), '{}')]".format(FILETAG))
        # if there is some attached file we set the attachments
        if filetags:
            message = set_attachs(filetags, envelope, headers)
        # else just the envelope
        else:
            message = etree_to_string(envelope)
        # post the data.
        return self.post(address, message, headers)
