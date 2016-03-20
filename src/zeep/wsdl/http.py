from lxml import etree

from zeep.wsdl.definitions import Binding


NSMAP = {
    'http': 'http://schemas.xmlsoap.org/wsdl/http/',
}


class HttpBinding(Binding):

    @classmethod
    def match(cls, node):
        http_node = node.find(etree.QName(NSMAP['http'], 'binding'))
        return http_node is not None
