import pprint

import requests

from zeep import xsd
from zeep.parser import parse_xml
from zeep.types import Schema
from zeep.utils import get_qname

NSMAP = {
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'soap12': 'http://schemas.xmlsoap.org/wsdl/soap12/',
}


class WSDL(object):
    def __init__(self, filename):
        self.types = {}
        self.schema_references = {}

        if filename.startswith(('http://', 'https://')):
            response = requests.get(filename)
            doc = parse_xml(response.content, self.schema_references)
        else:
            with open(filename) as fh:
                doc = parse_xml(fh.read(), self.schema_references)

        self.target_namespace = doc.get('targetNamespace')
        self.nsmap = doc.nsmap

        self.types = self.parse_types(doc)
        self.messages = self.parse_messages(doc)
        self.ports = self.parse_ports(doc)
        self.bindings = self.parse_binding(doc)
        self.services = self.parse_service(doc)

    def dump(self):
        print "Types: "
        pprint.pprint(self.types)
        print "Messages: "
        pprint.pprint(self.messages)
        print "Ports: "
        pprint.pprint(self.ports)
        print "Bindings: "
        pprint.pprint(self.bindings)
        print "Services: "
        pprint.pprint(self.services)

    def parse_types(self, doc):
        schema_nodes = doc.findall("wsdl:types/xsd:schema", namespaces=NSMAP)
        if not schema_nodes:
            return Schema()

        import_tag = '{http://www.w3.org/2001/XMLSchema}import'
        for schema_node in schema_nodes:
            tns = schema_node.get('targetNamespace')
            self.schema_references['intschema+%s' % tns] = schema_node

        for schema_node in schema_nodes:
            for import_node in schema_node.findall(import_tag):
                if import_node.get('schemaLocation'):
                    continue
                namespace = import_node.get('namespace')
                import_node.set('schemaLocation', 'intschema+%s' % namespace)

        return Schema(schema_nodes[0], self.schema_references)

    def parse_messages(self, doc):
        result = {}
        tns = doc.get('targetNamespace')

        messages = doc.findall("wsdl:message", namespaces=NSMAP)
        for message in messages:
            name = get_qname(message, 'name', tns)
            result[name] = {}

            for part in message.findall('wsdl:part', namespaces=NSMAP):
                part_name = get_qname(part, 'name', tns)

                part_element = get_qname(part, 'element', tns)
                if part_element is not None:
                    part_type = self.types.get_element(part_element)
                else:
                    part_type = get_qname(part, 'type', tns)
                    part_type = self.types.get_type(part_type)
                    part_type = xsd.Element(part_name, type_=part_type())

                result[name][part_name] = part_type

        return result

    def parse_ports(self, doc):
        findall = lambda node, name: node.findall(name, namespaces=NSMAP)
        tns = doc.get('targetNamespace')

        result = {}
        for port_node in findall(doc, 'wsdl:portType'):
            port_name = get_qname(port_node, 'name', tns)
            result[port_name] = port_info = {}

            for op_node in findall(port_node, 'wsdl:operation'):
                operation_name = get_qname(op_node, 'name', tns)
                port_info[operation_name] = {}

                for type_ in 'input', 'output', 'fault':
                    msg_node = op_node.find('wsdl:%s' % type_, namespaces=NSMAP)
                    if msg_node is not None:
                        message_name = get_qname(msg_node, 'message', tns)
                        port_info[operation_name][type_] = self.messages[message_name]
                    else:
                        port_info[operation_name][type_] = None
        return result

    def parse_binding(self, doc):
        findall = lambda node, name: node.findall(name, namespaces=NSMAP)
        tns = doc.get('targetNamespace')
        bindings = {}

        for binding_node in findall(doc, 'wsdl:binding'):
            name = get_qname(binding_node, 'name', tns)
            port_type = get_qname(binding_node, 'type', tns)
            ports = self.ports[port_type]

            # The soap:binding element contains the transport method and
            # default style attribute for the operations.
            soap_node = get_soap_node(binding_node, 'binding')
            transport = soap_node.get('transport')
            if transport != 'http://schemas.xmlsoap.org/soap/http':
                raise NotImplementedError("Only soap/http is supported for now")
            default_style = soap_node.get('style', 'document')

            bindings[name] = binding_info = {}
            for operation_node in findall(binding_node, 'wsdl:operation'):
                operation_name = get_qname(operation_node, 'name', tns)
                port_info = ports[operation_name]

                # The soap:operation element is required for soap/http bindings
                # and may be omitted for other bindings.
                soap_node = get_soap_node(operation_node, 'operation')
                action = None
                if soap_node is not None:
                    action = soap_node.get('soapAction')
                    style = soap_node.get('style', default_style)
                else:
                    style = default_style

                binding_info[operation_name] = {
                    'action': action,
                    'style': style,
                    'input': port_info['input'],
                    'output': port_info['output'],
                }

        return bindings

    def parse_service(self, doc):
        findall = lambda node, name: node.findall(name, namespaces=NSMAP)
        tns = doc.get('targetNamespace')
        result = {}
        for service_node in findall(doc, 'wsdl:service'):
            name = service_node.get('name')
            result[name] = {}

            for port_node in findall(service_node, 'wsdl:port'):
                soap_node = get_soap_node(port_node, 'address')
                binding = get_qname(port_node, 'binding', tns)
                port_name = get_qname(port_node, 'name', tns)

                result[name][port_name] = {
                    'binding': self.bindings[binding],
                    'address': soap_node.get('location'),
                }
        return result


def get_soap_node(parent, name):
    for ns in ['soap', 'soap12']:
        node = parent.find('%s:%s' % (ns, name), namespaces=NSMAP)
        if node is not None:
            return node
