from __future__ import print_function

import operator
from collections import OrderedDict

import six
from lxml import etree
from lxml.etree import QName

from zeep.parser import absolute_location, load_external, parse_xml
from zeep.utils import findall_multiple_ns
from zeep.wsdl import definitions, http, soap
from zeep.xsd import Schema
from zeep.xsd.context import ParserContext

NSMAP = {
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
}


class WSDL(object):
    def __init__(self, location, transport):
        self.location = location if not hasattr(location, 'read') else None
        self.transport = transport

        # Dict with all definition objects within this WSDL
        self._definitions = {}

        # Dict with internal schema objects, used for lxml.ImportResolver
        self._parser_context = ParserContext()

        document = self._load_content(location)

        root_definitions = Definitions(self, document, self.location)
        root_definitions.resolve_imports()

        # Make the wsdl definitions public
        self.schema = root_definitions.schema
        self.messages = root_definitions.messages
        self.port_types = root_definitions.port_types
        self.bindings = root_definitions.bindings
        self.services = root_definitions.services

    def __repr__(self):
        return '<WSDL(location=%r)>' % self.location

    def dump(self):

        print('')
        print("Prefixes:")
        for prefix, namespace in self.schema._prefix_map.items():
            print(' ' * 4, '%s: %s' % (prefix, namespace))

        type_instances = self.schema.types
        print('')
        print("Global types:")
        for type_obj in sorted(type_instances, key=lambda k: six.text_type(k)):
            print(' ' * 4, six.text_type(type_obj))

        print('')
        for service in self.services.values():
            print(six.text_type(service))
            for port in service.ports.values():
                print(' ' * 4, six.text_type(port))
                print(' ' * 8, 'Operations:')

                operations = sorted(
                    port.binding._operations.values(),
                    key=operator.attrgetter('name'))

                for operation in operations:
                    print('%s%s' % (' ' * 12, six.text_type(operation)))
                print('')

    def _load_content(self, location):
        if hasattr(location, 'read'):
            return self._parse_content(location.read())
        return load_external(
            location, self.transport, self._parser_context, self.location)

    def _parse_content(self, content, base_url=None):
        return parse_xml(
            content, self.transport, self._parser_context, base_url)


class Definitions(object):
    def __init__(self, wsdl, doc, location):
        self.wsdl = wsdl
        self.location = location

        self.schema = None
        self.port_types = {}
        self.messages = {}
        self.bindings = {}
        self.services = OrderedDict()

        self.imports = {}

        self.target_namespace = doc.get('targetNamespace')
        self.wsdl._definitions[self.target_namespace] = self
        self.nsmap = doc.nsmap

        # Process the definitions
        self.parse_imports(doc)

        self.schema = self.parse_types(doc)
        self.messages = self.parse_messages(doc)
        self.port_types = self.parse_ports(doc)
        self.bindings = self.parse_binding(doc)
        self.services = self.parse_service(doc)

    def __repr__(self):
        return '<Definitions(location=%r)>' % self.location

    def resolve_imports(self):
        """
            A -> B -> C -> D

            Items defined in D are only available in C, not in A or B.

        """
        for namespace, definition in self.imports.items():
            self.merge(definition, namespace)

        imports = self.imports.copy()
        self.imports = {}

        for definition in imports.values():
            definition.resolve_imports()

        for message in self.messages.values():
            message.resolve(self)

        for port_type in self.port_types.values():
            port_type.resolve(self)

        for binding in self.bindings.values():
            binding.resolve(self)

        for service in self.services.values():
            service.resolve(self)

    def merge(self, other, namespace):
        """Merge another `WSDL` instance in this object."""
        def filter_namespace(source, namespace):
            return {
                k: v for k, v in source.items()
                if k.startswith('{%s}' % namespace)
            }

        if not self.schema:
            self.schema = other.schema

        self.port_types.update(filter_namespace(other.port_types, namespace))
        self.messages.update(filter_namespace(other.messages, namespace))
        self.bindings.update(filter_namespace(other.bindings, namespace))
        self.services.update(filter_namespace(other.services, namespace))

        if namespace not in self.wsdl._definitions:
            self._definitions[namespace] = other

    def parse_imports(self, doc):
        """Import other WSDL documents in this document.

        Note that imports are non-transitive, so only import definitions
        which are defined in the imported document and ignore definitions
        imported in that document.

        This should handle recursive imports though:

            A -> B -> A
            A -> B -> C -> A

        """
        for import_node in doc.findall("wsdl:import", namespaces=NSMAP):
            location = import_node.get('location')
            namespace = import_node.get('namespace')

            location = absolute_location(location, self.location)

            if namespace in self.wsdl._definitions:
                self.imports[namespace] = self.wsdl._definitions[namespace]
            else:

                document = self.wsdl._load_content(location)
                if etree.QName(document.tag).localname == 'schema':
                    self.schema = Schema(
                        document, self.wsdl.transport, location,
                        self.wsdl._parser_context, location)
                else:
                    wsdl = Definitions(self.wsdl, document, location)
                    self.imports[namespace] = wsdl

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
        if types is None:
            return

        schema_nodes = findall_multiple_ns(types, 'xsd:schema', namespace_sets)
        if not schema_nodes:
            return None

        # FIXME: This fixes `test_parse_types_nsmap_issues`, lame solution...
        schema_nodes = [
            self.wsdl._parse_content(etree.tostring(schema_node), self.location)
            for schema_node in schema_nodes
        ]

        if len(schema_nodes) == 1:
            return Schema(
                schema_nodes[0], self.wsdl.transport, self.location,
                self.wsdl._parser_context, self.location)

        # A wsdl can container multiple schema nodes. The can import each
        # other by simply referencing by the namespace. To handle this in a
        # way that lxml schema can also handle it we create a new root schema
        # which imports the other schemas. This seems to work fine, although
        # I'm not sure how the non-transitive nature of imports impact it.

        # Create namespace mapping (namespace -> internal location)
        schema_ns = {}
        for i, schema_node in enumerate(schema_nodes):
            ns = schema_node.get('targetNamespace')
            int_name = schema_ns[ns] = 'intschema:xsd%d' % i
            self.wsdl._parser_context.schema_nodes.add(schema_ns[ns], schema_node)
            self.wsdl._parser_context.schema_locations[int_name] = self.location

        # Only handle the import statements from the 2001 xsd's for now
        import_tag = QName('http://www.w3.org/2001/XMLSchema', 'import').text

        # Create a new schema node with xsd:import statements for all
        # schema's listed here.
        root = etree.Element(
            etree.QName('http://www.w3.org/2001/XMLSchema', 'schema'))
        for i, schema_node in enumerate(schema_nodes):
            import_node = etree.Element(
                etree.QName('http://www.w3.org/2001/XMLSchema', 'import'))
            import_node.set('schemaLocation', 'intschema:xsd%d' % i)
            if schema_node.get('targetNamespace'):
                import_node.set('namespace', schema_node.get('targetNamespace'))
            root.append(import_node)

            # Add the namespace mapping created earlier here to the import
            # statements.
            for import_node in schema_node.findall(import_tag):
                if import_node.get('schemaLocation'):
                    continue
                namespace = import_node.get('namespace')
                import_node.set('schemaLocation', schema_ns[namespace])

        schema_node = root
        return Schema(
            schema_node, self.wsdl.transport, self.location,
            self.wsdl._parser_context, self.location)

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
            if soap.Soap11Binding.match(binding_node):
                binding = soap.Soap11Binding.parse(self, binding_node)
            elif soap.Soap12Binding.match(binding_node):
                binding = soap.Soap12Binding.parse(self, binding_node)
            elif http.HttpGetBinding.match(binding_node):
                binding = http.HttpGetBinding.parse(self, binding_node)
            elif http.HttpPostBinding.match(binding_node):
                binding = http.HttpPostBinding.parse(self, binding_node)
            else:
                continue

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
        result = OrderedDict()
        for service_node in doc.findall('wsdl:service', namespaces=NSMAP):
            service = definitions.Service.parse(self, service_node)
            result[service.name] = service
        return result
