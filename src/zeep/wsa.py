import uuid

from lxml import etree
from lxml.builder import ElementMaker

from zeep.plugins import Plugin
from zeep.wsdl.utils import get_or_create_header

WSA = ElementMaker(namespace='http://www.w3.org/2005/08/addressing')


class WsAddressingPlugin(Plugin):
    def egress(self, envelope, http_headers, operation, binding_options, op_args, op_kwargs):
        """Apply the ws-addressing headers to the given envelope."""

        wsa_action = operation.input.abstract.wsa_action
        if not wsa_action:
            wsa_action = operation.soapaction

        header = get_or_create_header(envelope)
        headers = [
            WSA.Action(wsa_action),
            WSA.MessageID('urn:uuid:' + str(uuid.uuid4())),
            WSA.To(binding_options['address']),
        ]
        header.extend(headers)
        etree.cleanup_namespaces(
            envelope, top_nsmap={
                'wsa': 'http://www.w3.org/2005/08/addressing'
            })

        return envelope, http_headers
