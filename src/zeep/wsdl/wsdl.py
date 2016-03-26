from __future__ import print_function

import six
from lxml import etree
from lxml.etree import QName

from zeep.parser import parse_xml
from zeep.utils import findall_multiple_ns
from zeep.wsdl import definitions, http, soap
from zeep.xsd import Schema

NSMAP = {
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'soap12': 'http://schemas.xmlsoap.org/wsdl/soap12/',
    'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
    'http': 'http://schemas.xmlsoap.org/wsdl/http/',
    'mime': 'http://schemas.xmlsoap.org/wsdl/mime/',
}


class WSDL(object):
    def __init__(self, filename, transport):
        self.transport = transport
        self.schema = None
        self.ports = {}
        self.messages = {}
        self.bindings = {}
        self.services = {}
        self.namespaces = []
        self.schema_references = {}

        if filename.startswith(('http://', 'https://')):
            response = transport.load(filename)
            doc = self._parse_content(response)
        else:
            with open(filename, mode='rb') as fh:
                doc = self._parse_content(fh.read())

        self.nsmap = doc.nsmap
        self.target_namespace = doc.get('targetNamespace')
        self.namespaces.append(self.target_namespace)

        # Process the definitions
        self.parse_imports(doc)
        schema = self.parse_types(doc)
        if schema and self.schema:
            raise ValueError("Multiple XSD schema's defined")
        self.schema = self.schema or schema
        self.messages.update(self.parse_messages(doc))
        self.ports.update(self.parse_ports(doc))
        self.bindings.update(self.parse_binding(doc))
        self.services.update(self.parse_service(doc))

    def _parse_content(self, content):
        return parse_xml(content, self.transport, self.schema_references)

    def dump(self):
        type_instances = self.schema.types
        print('Types:')
        for type_obj in sorted(type_instances, key=lambda k: six.text_type(k)):
            print(' ' * 4, six.text_type(type_obj))

        print('')

        for service in self.services.values():
            print(six.text_type(service))
            for port in service.ports.values():
                print(' ' * 4, six.text_type(port))
                print(' ' * 8, 'Operations:')
                for operation in port.binding.operations.values():
                    print('%s%s' % (' ' * 12, six.text_type(operation)))

    def merge(self, other, namespace, transitive=False):
        """Merge another `WSDL` instance in this object."""
        def filter_namespace(source, namespace):
            return {
                k: v for k, v in source.items()
                if k.startswith('{%s}' % namespace)
            }

        self.schema = other.schema
        self.ports.update(filter_namespace(other.ports, namespace))
        self.messages.update(filter_namespace(other.messages, namespace))
        self.bindings.update(filter_namespace(other.bindings, namespace))
        self.services.update(filter_namespace(other.services, namespace))
        self.namespaces.append(namespace)

    def parse_imports(self, doc):
        """Import other WSDL documents in this document.

        Note that imports are non-transitive, so only import definitions
        which are defined in the imported document and ignore definitions
        imported in that document.

        """
        for import_node in doc.findall("wsdl:import", namespaces=NSMAP):
            location = import_node.get('location')
            namespace = import_node.get('namespace')
            wsdl = WSDL(location, self.transport)
            self.merge(wsdl, namespace)

    def parse_types(self, doc):
        """Return a `types.Schema` instance.

        Note that a WSDL can contain multiple XSD schema's. The schemas can
        reference import each other using xsd:import statements.

            <definitions .... >
                <types>
                    <xsd:schema .... />*
                </types>
            </definitions>

        """
        namespace_sets = [
            {'xsd': 'http://www.w3.org/2001/XMLSchema'},
            {'xsd': 'http://www.w3.org/1999/XMLSchema'},
        ]

        types = doc.find('wsdl:types', namespaces=NSMAP)

        schema_nodes = findall_multiple_ns(types, 'xsd:schema', namespace_sets)
        if not schema_nodes:
            return None

        # FIXME: This fixes `test_parse_types_nsmap_issues`, lame solution...
        schema_nodes = [
            self._parse_content(etree.tostring(schema_node))
            for schema_node in schema_nodes
        ]

        for schema_node in schema_nodes:
            tns = schema_node.get('targetNamespace')
            self.schema_references['intschema+%s' % tns] = schema_node

        # Only handle the import statements from the 2001 xsd's for now
        import_tag = QName('http://www.w3.org/2001/XMLSchema', 'import').text
        for schema_node in schema_nodes:
            for import_node in schema_node.findall(import_tag):
                if import_node.get('schemaLocation'):
                    continue
                namespace = import_node.get('namespace')
                import_node.set('schemaLocation', 'intschema+%s' % namespace)

        schema_node = schema_nodes[0]

        return Schema(
            schema_node, self.transport, self.schema_references)

    def parse_messages(self, doc):
        """
            <definitions .... >
                <message name="nmtoken"> *
                    <part name="nmtoken" element="qname"? type="qname"?/> *
                </message>
            </definitions>
        """
        result = {}
        for msg_node in doc.findall("wsdl:message", namespaces=NSMAP):
            msg = definitions.AbstractMessage.parse(self, msg_node)
            result[msg.name.text] = msg
        return result

    def parse_ports(self, doc):
        """Return dict with `PortType` instances as values

            <wsdl:definitions .... >
                <wsdl:portType name="nmtoken">
                    <wsdl:operation name="nmtoken" .... /> *
                </wsdl:portType>
            </wsdl:definitions>
        """
        result = {}
        for port_node in doc.findall('wsdl:portType', namespaces=NSMAP):
            port_type = definitions.PortType.parse(self, port_node)
            result[port_type.name.text] = port_type
        return result

    def parse_binding(self, doc):
        """
            <wsdl:definitions .... >
                <wsdl:binding name="nmtoken" type="qname"> *
                    <-- extensibility element (1) --> *
                    <wsdl:operation name="nmtoken"> *
                       <-- extensibility element (2) --> *
                       <wsdl:input name="nmtoken"? > ?
                           <-- extensibility element (3) -->
                       </wsdl:input>
                       <wsdl:output name="nmtoken"? > ?
                           <-- extensibility element (4) --> *
                       </wsdl:output>
                       <wsdl:fault name="nmtoken"> *
                           <-- extensibility element (5) --> *
                       </wsdl:fault>
                    </wsdl:operation>
                </wsdl:binding>
            </wsdl:definitions>
        """
        result = {}
        for binding_node in doc.findall('wsdl:binding', namespaces=NSMAP):
            # Detect the binding type
            if soap.SoapBinding.match(binding_node):
                binding = soap.SoapBinding.parse(self, binding_node)
            elif http.HttpBinding.match(binding_node):
                binding = http.HttpBinding.parse(self, binding_node)
            result[binding.name.text] = binding
        return result

    def parse_service(self, doc):
        """
            <wsdl:definitions .... >
                <wsdl:service .... > *
                    <wsdl:port name="nmtoken" binding="qname"> *
                       <-- extensibility element (1) -->
                    </wsdl:port>
                </wsdl:service>
            </wsdl:definitions>
        """
        result = {}
        for service_node in doc.findall('wsdl:service', namespaces=NSMAP):
            service = definitions.Service.parse(self, service_node)
            result[service.name.text] = service
        return result
