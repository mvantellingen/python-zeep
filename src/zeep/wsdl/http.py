from lxml import etree

from zeep import xsd
from zeep.utils import qname_attr
from zeep.wsdl.definitions import Binding, ConcreteMessage, Operation

NSMAP = {
    'http': 'http://schemas.xmlsoap.org/wsdl/http/',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'mime': 'http://schemas.xmlsoap.org/wsdl/mime/',
}


class HttpBinding(Binding):

    @classmethod
    def match(cls, node):
        http_node = node.find(etree.QName(NSMAP['http'], 'binding'))
        return http_node is not None

    @classmethod
    def parse(cls, wsdl, xmlelement):
        name = qname_attr(xmlelement, 'name', wsdl.target_namespace)
        port_name = qname_attr(xmlelement, 'type', wsdl.target_namespace)
        port_type = wsdl.ports[port_name.text]

        obj = cls(name, port_type)

        for node in xmlelement.findall('wsdl:operation', namespaces=NSMAP):
            operation = HttpOperation.parse(wsdl, node, obj)

            # XXX: operation name is not unique
            obj.operations[operation.name.text] = operation
        return obj

    def process_service_port(self, xmlelement):
        address_node = xmlelement.find('http:address', namespaces=NSMAP)
        if address_node is None:
            raise ValueError("No `http:address` node found")

        return {
            'address': address_node.get('location')
        }


class HttpOperation(Operation):

    @classmethod
    def parse(cls, wsdl, xmlelement, binding):
        localname = xmlelement.get('name')

        for namespace in wsdl.namespaces:
            name = etree.QName(namespace, localname)
            if name in binding.port_type.operations:
                abstract_operation = binding.port_type.operations[name]
                break
        else:
            raise ValueError("Operation not found")

        obj = cls(name, abstract_operation)

        http_operation = xmlelement.find('http:operation', namespaces=NSMAP)
        http_operation.get('location')

        for node in xmlelement.getchildren():
            tag_name = etree.QName(node.tag).localname
            if tag_name not in ('input', 'output'):
                continue

            abstract = getattr(abstract_operation, tag_name)

            message_node = node.getchildren()[0]
            message_class = None
            if message_node.tag == etree.QName(NSMAP['http'], 'urlEncoded'):
                message_class = UrlEncoded

            elif message_node.tag == etree.QName(NSMAP['mime'], 'content'):
                message_class = MimeContent

            if message_class:
                msg = message_class.parse(wsdl, node, abstract, obj)
                setattr(obj, tag_name, msg)
        return obj


class UrlEncoded(ConcreteMessage):

    @classmethod
    def parse(cls, wsdl, xmlelement, abstract_message, operation):
        obj = cls(wsdl, abstract_message, operation)
        obj.params = xsd.Element(
            None,
            xsd.ComplexType(children=abstract_message.parts.values()))
        return obj

    def signature(self):
        return self.params.type.signature()


class MimeContent(ConcreteMessage):

    @classmethod
    def parse(cls, wsdl, xmlelement, abstract_message, operation):
        obj = cls(wsdl, abstract_message, operation)
        obj.params = xsd.Element(
            None,
            xsd.ComplexType(children=abstract_message.parts.values()))
        return obj

    def signature(self):
        return self.params.type.signature()


class MimeXML(ConcreteMessage):
    pass


class MimeMultipart(ConcreteMessage):
    pass
