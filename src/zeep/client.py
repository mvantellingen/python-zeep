import logging

from zeep.transports import Transport
import requests
from lxml import etree
from lxml.builder import ElementMaker

from zeep.utils import parse_qname
from zeep.wsdl import WSDL

NSMAP = {
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
}


logger = logging.getLogger(__name__)


class Client(object):

    def __init__(self, wsdl):
        self.wsdl = WSDL(wsdl)

    def call(self, name, *args, **kwargs):
        transport = Transport()
        port = self.get_port()
        print port.send(transport, name, args, kwargs)


    def get_port(self, service=None, port=None):
        service = self.wsdl.services.values()[0]
        return service.ports.values()[0]

        name = parse_qname(name, self.wsdl.nsmap, self.wsdl.target_namespace)
        name = name.text

        operation = None
        for port in service.ports.values():
            operation = port.binding.get(name)
            if operation:
                break

        if not operation:
            raise TypeError("No such function for service: %r" % name)
        return port, operation

    def process_response(self, name, response):
        port, operation = self.get_binding(name)
        response_node = etree.fromstring(response)
        node = response_node.find('soap-env:Body', namespaces=NSMAP)

        if operation.style == 'rpc':
            tag_name = etree.QName(
                operation.protocol['output']['namespace'],
                operation.output.name.localname)

            value = node.find(tag_name)
            result = []
            for element in operation.output.parts.values():
                elm = value.find(element.name)
                result.append(element.parse(elm))

        else:
            result = []
            for element in operation.output.parts.values():
                elm = node.find(element.qname)
                assert elm is not None
                result.append(element.parse(elm))

        if len(result) > 1:
            return tuple(result)
        return result[0]


def create_soap_message():
    soap = ElementMaker(namespace=NSMAP['soap-env'], nsmap=NSMAP)
    return soap.Envelope(
        soap.Body()
    )
