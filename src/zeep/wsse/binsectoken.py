"""
    zeep.wsse.binsetoken
    ~~~~~~~~~~~~~~~~~~~~

    Library to sign SOAP requests with WSSE tokens.

"""
import base64
import logging
import os
from uuid import uuid4

from lxml import etree
from OpenSSL import crypto

try:
    import dm.xmlsec.binding as xmlsec
    from dm.xmlsec.binding.tmpl import Signature
except ImportError:
    raise ImportError(
        "The dm.xmlsec.binding is required when using the BinarySecurityToken")


class ns:
    dsns = ('ds', 'http://www.w3.org/2000/09/xmldsig#')  # NOQA
    ecns = ('ec', 'http://www.w3.org/2001/10/xml-exc-c14n#')  # NOQA
    envns = ('SOAP-ENV', 'http://schemas.xmlsoap.org/soap/envelope/')  # NOQA
    wssens = ('wsse', 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd')  # NOQA
    wssns = ('wss', 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#')  # NOQA
    wsuns = ('wsu', 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd')  # NOQA

    NSMAP = dict((envns, dsns, wssens, wsuns, wssns))


logger = logging.getLogger(__name__)


BODY_XPATH = etree.XPath(
    '/SOAP-ENV:Envelope/SOAP-ENV:Body', namespaces=ns.NSMAP)
HEADER_XPATH = etree.XPath(
    '/SOAP-ENV:Envelope/SOAP-ENV:Header', namespaces=ns.NSMAP)
SECURITY_XPATH = etree.XPath('wsse:Security', namespaces=ns.NSMAP)
TIMESTAMP_XPATH = etree.XPath('wsu:Timestamp', namespaces=ns.NSMAP)

C14N = 'http://www.w3.org/2001/10/xml-exc-c14n#'
XMLDSIG_SHA1 = 'http://www.w3.org/2000/09/xmldsig#sha1'


class BinarySecurityToken(object):

    def __init__(self, filename):
        self.cert_filename = filename

    def sign(self, envelope, http_headers):
        new_envelope = sign_envelope(envelope, self.cert_filename)
        return new_envelope, http_headers

    def verify(self, doc):
        valid = verify_envelope(doc, self.cert_filename)
        if not valid:
            raise CertificationError("Failed to verify response")


def ns_id(tagname, suds_ns):
    return '{{{0}}}{1}'.format(suds_ns[1], tagname)

WSU_ID = ns_id('Id', ns.wsuns)
BINARY_TOKEN_TYPE = (
    'http://docs.oasis-open.org/wss/2004/01/' +
    'oasis-200401-wss-x509-token-profile-1.0#X509v3')


def log_errors(filename, line, func, errorObject, errorSubject, reason, msg):
    info = []
    if errorObject != 'unknown':
        info.append('obj=' + errorObject)
    if errorSubject != 'unknown':
        info.append('subject=' + errorSubject)
    if msg.strip():
        info.append('msg=' + msg)
    if info:
        logger.debug('%s:%d(%s)' % (filename, line, func), ' '.join(info))


class CertificationError(Exception):
    pass


# Initialize the xmlsec library
xmlsec.initialize()
xmlsec.set_error_callback(log_errors)


class SignQueue(object):
    WSU_ID = ns_id('Id', ns.wsuns)
    DS_DIGEST_VALUE = ns_id('DigestValue', ns.dsns)
    DS_REFERENCE = ns_id('Reference', ns.dsns)
    DS_TRANSFORMS = ns_id('Transforms', ns.dsns)

    def __init__(self):
        self.queue = []

    def push_and_mark(self, element):
        unique_id = get_unique_id()
        element.set(self.WSU_ID, unique_id)
        self.queue.append(unique_id)

    def insert_references(self, signature):
        signed_info = signature.find('ds:SignedInfo', namespaces=ns.NSMAP)
        nsmap = {ns.ecns[0]: ns.ecns[1]}

        for element_id in self.queue:
            reference = etree.SubElement(
                signed_info, self.DS_REFERENCE,
                {'URI': '#{0}'.format(element_id)})
            transforms = etree.SubElement(reference, self.DS_TRANSFORMS)
            node = set_algorithm(transforms, 'Transform', C14N)

            elm = _create_element(node, 'ec:InclusiveNamespaces', nsmap)
            elm.set('PrefixList', 'urn')

            set_algorithm(reference, 'DigestMethod', XMLDSIG_SHA1)
            etree.SubElement(reference, self.DS_DIGEST_VALUE)


def sign_envelope(doc, key_file):
    """Sign the given soap request with the given key"""
    body = get_body(doc)

    queue = SignQueue()
    queue.push_and_mark(body)

    security_node = ensure_security_header(doc, queue)
    security_token_node = create_binary_security_token(key_file)
    signature_node = Signature(
        xmlsec.TransformExclC14N, xmlsec.TransformRsaSha1)

    security_node.append(security_token_node)
    security_node.append(signature_node)
    queue.insert_references(signature_node)

    key_info = create_key_info_node(security_token_node)
    signature_node.append(key_info)

    # Sign the generated xml
    xmlsec.addIDs(doc, ['Id'])
    dsigCtx = xmlsec.DSigCtx()
    dsigCtx.signKey = xmlsec.Key.load(key_file, xmlsec.KeyDataFormatPem, None)
    dsigCtx.sign(signature_node)
    return doc


def verify_envelope(doc, key_file):
    """Verify that the given soap request is signed with the certificate"""
    node = doc.find(".//{%s}Signature" % xmlsec.DSigNs)
    if node is None:
        raise CertificationError("No signature node found")
    dsigCtx = xmlsec.DSigCtx()

    xmlsec.addIDs(doc, ['Id'])
    signKey = xmlsec.Key.load(key_file, xmlsec.KeyDataFormatPem)
    signKey.name = os.path.basename(key_file)

    dsigCtx.signKey = signKey
    try:
        dsigCtx.verify(node)
    except xmlsec.VerificationError:
        return False
    return True


def get_unique_id():
    return 'id-{0}'.format(uuid4())


def set_algorithm(parent, name, value):
    return etree.SubElement(parent, ns_id(name, ns.dsns), {'Algorithm': value})


def get_body(envelope):
    (body,) = BODY_XPATH(envelope)
    return body


def create_key_info_node(security_token):
    """Create the KeyInfo node for WSSE.

    Note that this currently only supports BinarySecurityTokens

    Example of the generated XML:

        <ds:KeyInfo Id="KI-24C56C5B3448F4BE9D141094243396829">
            <wsse:SecurityTokenReference
                wsse11:TokenType="{{ BINARY_TOKEN_TYPE }}">
                <wsse:Reference
                    URI="#X509-24C56C5B3448F4BE9D141094243396828"
                    ValueType="{{ BINARY_TOKEN_TYPE }}"/>
           </wsse:SecurityTokenReference>
        </ds:KeyInfo>

    """
    key_info = etree.Element(ns_id('KeyInfo', ns.dsns))

    sec_token_ref = etree.SubElement(
        key_info, ns_id('SecurityTokenReference', ns.wssens))
    sec_token_ref.set(
        ns_id('TokenType', ns.wssens), security_token.get('ValueType'))

    reference = etree.SubElement(sec_token_ref, ns_id('Reference', ns.wssens))
    reference.set('ValueType', security_token.get('ValueType'))
    reference.set('URI', '#%s' % security_token.get(WSU_ID))
    return key_info


def create_binary_security_token(key_file):
    """Create the BinarySecurityToken node containing the x509 certificate.

    """
    node = etree.Element(
        ns_id('BinarySecurityToken', ns.wssens),
        nsmap={ns.wssens[0]: ns.wssens[1]})
    node.set(ns_id('Id', ns.wsuns), get_unique_id())
    node.set('EncodingType', ns.wssns[1] + 'Base64Binary')
    node.set('ValueType', BINARY_TOKEN_TYPE)

    with open(key_file) as fh:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, fh.read())
        node.text = base64.b64encode(
            crypto.dump_certificate(crypto.FILETYPE_ASN1, cert))
    return node


def ensure_security_header(envelope, queue):
    """Insert a security XML node if it doesn't exist otherwise update it.

    """
    headers = HEADER_XPATH(envelope)
    if not headers:
        header = etree.Element(
            '{http://schemas.xmlsoap.org/soap/envelope/}Header')
        envelope.insert(0, header)
    else:
        header = headers[0]

    security = SECURITY_XPATH(header)
    if security:
        for timestamp in TIMESTAMP_XPATH(security[0]):
            queue.push_and_mark(timestamp)
        return security[0]
    else:
        nsmap = {
            'wsu': ns.wsuns[1],
            'wsse': ns.wssens[1],
        }
        return _create_element(header, 'wsse:Security', nsmap)


def _create_element(parent, name, nsmap):
    prefix, name = name.split(':', 1)
    tag_name = '{%s}%s' % (nsmap[prefix], name)

    if parent is not None:
        return etree.SubElement(parent, tag_name, nsmap=nsmap)
    else:
        return etree.Element(tag_name, nsmap=nsmap)
