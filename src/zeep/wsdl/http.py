from lxml import etree
from zeep.utils import get_qname

from zeep.wsdl.definitions import Binding


NSMAP = {
    'http': 'http://schemas.xmlsoap.org/wsdl/http/',
}


class HttpBinding(Binding):

    @classmethod
    def match(cls, node):
        http_node = node.find(etree.QName(NSMAP['http'], 'binding'))
        return http_node is not None

    @classmethod
    def parse(cls, wsdl, xmlelement):
        name = get_qname(
            xmlelement, 'name', wsdl.target_namespace, as_text=False)
        port_name = get_qname(xmlelement, 'type', wsdl.target_namespace)
        port_type = wsdl.ports[port_name]

        obj = cls(name, port_type)
        return obj

    def process_service_port(self, xmlelement):
        address_node = xmlelement.find('http:address', namespaces=NSMAP)
        if address_node is None:
            raise ValueError("No `http:address` node found")

        return {
            'address': address_node.get('location')
        }
