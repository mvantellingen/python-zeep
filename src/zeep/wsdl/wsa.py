import uuid

from lxml import etree
from lxml.builder import ElementMaker

from zeep.wsdl.utils import get_or_create_header

WSA = ElementMaker(namespace='http://www.w3.org/2005/08/addressing')


def apply(to_addr, operation, envelope, http_headers):
    """Apply the ws-addressing headers to the given envelope."""
    if operation.input.abstract.wsa_action:
        header = get_or_create_header(envelope)
        headers = [
            WSA.Action(operation.input.abstract.wsa_action),
            WSA.MessageID('urn:uuid:' + str(uuid.uuid4())),
            WSA.To(to_addr),
        ]
        header.extend(headers)
        etree.cleanup_namespaces(
            envelope, top_nsmap={
                'wsa': 'http://www.w3.org/2005/08/addressing'
            })

    return envelope, http_headers
