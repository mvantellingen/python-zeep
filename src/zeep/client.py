import logging

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

    def call(self, name, **kwargs):
        service = self.wsdl.services.values()[0]
        name = parse_qname(name, self.wsdl.nsmap, self.wsdl.target_namespace)
        name = name.text

        port = None
        address = None
        for binding in service.values():
            port = binding['binding'].get(name)
            address = binding['address']
            if port:
                break

        if not port:
            raise TypeError("No such function for service: %r" % name)

        envelope = create_soap_message()
        body = envelope.find('soap-env:Body', namespaces=envelope.nsmap)

        if port['style'] == 'rpc':
            method = etree.SubElement(body, name)
            for key, value in kwargs.iteritems():
                key = parse_qname(key, self.wsdl.nsmap, self.wsdl.target_namespace)
                obj = port['input']['port']['parts'][key]
                obj.render(method, value)
        else:
            obj = port['input']['port']['parts'].values()[0]
            value = obj(**kwargs)
            obj.render(body, value)

        logger.debug("Sending XML:\n%s", etree.tostring(envelope, pretty_print=True))
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': port['action'],
        }
        response = requests.post(address, data=etree.tostring(envelope), headers=headers)

        if response.status_code != 200:
            raise NotImplementedError("No error handling yet!")

        response_node = etree.fromstring(response.content)
        node = response_node.find('soap-env:Body', namespaces=NSMAP)

        if port['style'] == 'rpc':
            tag_name = etree.QName(
                port['output']['namespace'],
                etree.QName(port['output']['port']['name']).localname)

            value = node.find(tag_name)
            result = []
            for element in port['output']['port']['parts'].values():
                elm = value.find(element.name)
                result.append(element.parse(elm))

        else:
            result = []
            for element in port['output']['port']['parts'].values():
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
