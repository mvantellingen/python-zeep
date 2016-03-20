from collections import OrderedDict

import requests
from lxml import etree
from lxml.builder import ElementMaker
from lxml.etree import QName

from zeep import xsd
from zeep.parser import parse_xml
from zeep.types import Schema
from zeep.utils import (
    findall_multiple_ns, get_qname, parse_qname, process_signature)

NSMAP = {
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'soap12': 'http://schemas.xmlsoap.org/wsdl/soap12/',
    'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
    'http': 'http://schemas.xmlsoap.org/wsdl/http/',
    'mime': 'http://schemas.xmlsoap.org/wsdl/mime/',
}


class AbstractMessage(object):
    def __init__(self, name):
        self.name = name
        self.parts = OrderedDict()

    def __repr__(self):
        return '<%s(name=%r)>' % (
            self.__class__.__name__, self.name.text)

    def add_part(self, name, element):
        self.parts[name.text] = element

    def get_part(self, name):
        return self.parts[name]

    @classmethod
    def parse(cls, wsdl, xmlelement):
        """
            <definitions .... >
                <message name="nmtoken"> *
                    <part name="nmtoken" element="qname"? type="qname"?/> *
                </message>
            </definitions>
        """
        msg = cls(name=get_qname(
            xmlelement, 'name', wsdl.target_namespace, as_text=False))

        for part in xmlelement.findall('wsdl:part', namespaces=NSMAP):
            part_name = get_qname(
                part, 'name', wsdl.target_namespace, as_text=False)
            part_element = get_qname(part, 'element', wsdl.target_namespace)

            if part_element is not None:
                part_type = wsdl.schema.get_element(part_element)
            else:
                part_type = get_qname(part, 'type', wsdl.target_namespace)
                part_type = wsdl.schema.get_type(part_type)
                part_type = xsd.Element(part_name, type_=part_type())
            msg.add_part(part_name, part_type)
        return msg


class AbstractOperation(object):
    def __init__(self, name, input=None, output=None, fault=None,
                 parameter_order=None):
        self.name = name
        self.input = input
        self.output = output
        self.fault = fault
        self.parameter_order = parameter_order

    @classmethod
    def parse(cls, wsdl, xmlelement):
        name = get_qname(
            xmlelement, 'name', wsdl.target_namespace, as_text=False)

        kwargs = {}
        for type_ in 'input', 'output', 'fault':
            msg_node = xmlelement.find('wsdl:%s' % type_, namespaces=NSMAP)
            if msg_node is None:
                continue
            message_name = get_qname(
                msg_node, 'message', wsdl.target_namespace)
            kwargs[type_] = wsdl.messages[message_name]

        kwargs['name'] = name
        kwargs['parameter_order'] = xmlelement.get('parameterOrder')
        return cls(**kwargs)


class PortType(object):
    def __init__(self, name):
        self.name = name
        self.operations = {}

    def __repr__(self):
        return '<%s(name=%r)>' % (
            self.__class__.__name__, self.name.text)

    @classmethod
    def parse(cls, wsdl, xmlelement):
        """
            <wsdl:definitions .... >
                <wsdl:portType name="nmtoken">
                    <wsdl:operation name="nmtoken" .... /> *
                </wsdl:portType>
            </wsdl:definitions>

        """
        name = get_qname(
            xmlelement, 'name', wsdl.target_namespace, as_text=False)
        obj = cls(name)

        for elm in xmlelement.findall('wsdl:operation', namespaces=NSMAP):
            operation = AbstractOperation.parse(wsdl, elm)
            obj.operations[operation.name.text] = operation
        return obj


class Binding(object):
    """
        Binding
           |
           +-> Operation
                   |
                   +-> ConcreteMessage
                             |
                             +-> AbstractMessage

    """
    def __init__(self, name, port_type):
        self.name = name
        self.port_type = port_type
        self.operations = {}

    def __repr__(self):
        return '<%s(name=%r, port_type=%r)>' % (
            self.__class__.__name__, self.name.text, self.port_type)

    def get(self, name):
        return self.operations[name]

    @classmethod
    def match(cls, node):
        raise NotImplementedError()


class SoapBinding(Binding):

    @classmethod
    def match(cls, node):
        soap_node = get_soap_node(node, 'binding')
        return soap_node is not None

    def send(self, transport, address, operation, args, kwargs):
        """Called from the service"""
        operation = self.get(operation)
        if not operation:
            raise ValueError("Operation not found")
        body, header, headerfault = operation.create(*args, **kwargs)

        soap = ElementMaker(namespace=NSMAP['soap-env'], nsmap=NSMAP)

        envelope = soap.Envelope()
        if header is not None:
            envelope.append(header)
        if body is not None:
            envelope.append(body)

        http_headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': operation.soapaction,
        }
        response = transport.post(
            address, etree.tostring(envelope), http_headers)
        return self.process_reply(operation, response)

    def process_reply(self, operation, response):
        if response.status_code != 200:
            return self.process_error(response.content)
            raise NotImplementedError("No error handling yet!")

        envelope = etree.fromstring(response.content)
        return operation.process_reply(envelope)

    def process_error(self, response):
        doc = etree.fromstring(response)
        fault_node = doc.find('soap-env:Body/soap-env:Fault', namespaces=NSMAP)
        message = 'unknown'
        if fault_node is not None:
            string_node = fault_node.find('faultstring')
            if string_node is not None:
                message = string_node.text

        raise IOError(message.strip())

    @classmethod
    def parse(cls, wsdl, xmlelement):
        name = get_qname(xmlelement, 'name', wsdl.target_namespace, as_text=False)
        port_name = get_qname(xmlelement, 'type', wsdl.target_namespace)
        port_type = wsdl.ports[port_name]

        obj = cls(name, port_type)

        # The soap:binding element contains the transport method and
        # default style attribute for the operations.
        soap_node = get_soap_node(xmlelement, 'binding')
        transport = soap_node.get('transport')
        if transport != 'http://schemas.xmlsoap.org/soap/http':
            raise NotImplementedError("Only soap/http is supported for now")
        default_style = soap_node.get('style', 'document')

        obj.transport = transport
        obj.default_style = default_style

        for node in xmlelement.findall('wsdl:operation', namespaces=NSMAP):
            operation = Operation.parse(wsdl, node, obj)

            # XXX: operation name is not unique
            obj.operations[operation.name.text] = operation

        return obj


class HttpBinding(Binding):

    @classmethod
    def match(cls, node):
        http_node = node.find(etree.QName(NSMAP['http'], 'binding'))
        return http_node is not None


class ConcreteMessage(object):
    def __init__(self, wsdl, abstract, operation):
        self.abstract = abstract
        self.wsdl = wsdl
        self.namespace = {}
        self.operation = operation

    def create(self, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def parse(cls, wsdl, xmlelement, abstract_message, operation):
        """
        Example::

              <output>
                <soap:body use="literal"/>
              </output>

        """
        obj = cls(wsdl, abstract_message, operation)

        body = get_soap_node(xmlelement, 'body')
        header = get_soap_node(xmlelement, 'header')
        headerfault = get_soap_node(xmlelement, 'headerfault')

        body_info = {}
        header_info = {}
        headerfault_info = {}

        if body is not None:
            body_info = {
                'part': get_qname(body, 'part', wsdl.target_namespace),
                'use': body.get('use', 'literal'),
                'encodingStyle': body.get('encodingStyle'),
                'namespace': body.get('namespace'),
            }

        if header is not None:
            header_info = {
                'message': get_qname(header, 'message', wsdl.target_namespace),
                'part': get_qname(header, 'part', wsdl.target_namespace),
                'use': header.get('use', 'literal'),
                'encodingStyle': header.get('encodingStyle'),
                'namespace': header.get('namespace'),
            }

        if headerfault is not None:
            headerfault_info = {
                'message': get_qname(headerfault, 'message', wsdl.target_namespace),
                'part': get_qname(headerfault, 'part', wsdl.target_namespace),
                'use': headerfault.get('use', 'literal'),
                'encodingStyle': headerfault.get('encodingStyle'),
                'namespace': headerfault.get('namespace'),
            }

        obj.namespace = {
            'body': body_info.get('namespace'),
            'header': header_info.get('namespace'),
            'headerfault': headerfault_info.get('namespace'),
        }

        part_names = abstract_message.parts.keys()
        if header_info:
            part_name = header_info['part']

            if header_info['message']:
                msg = wsdl.messages[header_info['message']]
                obj.header = msg.parts[part_name]
            else:
                part_names.remove(part_name)
                obj.header = abstract_message.parts[part_name]
        else:
            obj.header = None

        if headerfault_info:
            part_name = headerfault_info['part']
            part_names.remove(part_name)
            obj.headerfault = abstract_message.parts[part_name]
        else:
            obj.headerfault = None

        if body_info:
            part_name = body_info['part'] or part_names[0]
            part_names.remove(part_name)
            obj.body = abstract_message.parts[part_name]

        return obj

    def signature(self):
        # if self.operation.abstract.parameter_order:
        #     self.operation.abstract.parameter_order.split()
        return self.body.type.signature()


class RpcMessage(ConcreteMessage):
    def serialize(self, *args, **kwargs):
        soap = ElementMaker(namespace=NSMAP['soap-env'], nsmap=NSMAP)
        tag_name = etree.QName(
            self.namespace['body'], self.abstract.name.localname)

        body = soap.Body()
        method = etree.SubElement(body, tag_name)

        param_order = self.signature()
        items = process_signature(param_order, args, kwargs)
        for key, value in items.iteritems():
            key = parse_qname(key, self.wsdl.nsmap, self.wsdl.target_namespace)
            obj = self.abstract.get_part(key)
            obj.render(method, value)
        return body, None, None

    def deserialize(self, node):
        tag_name = etree.QName(
            self.namespace['body'], self.abstract.name.localname)

        value = node.find(tag_name)
        result = []
        for element in self.abstract.parts.values():
            elm = value.find(element.name)
            result.append(element.parse(elm))

        if len(result) > 1:
            return tuple(result)
        return result[0]

    def signature(self):
        # if self.operation.abstract.parameter_order:
        #     self.operation.abstract.parameter_order.split()
        return self.abstract.parts.keys()


class DocumentMessage(ConcreteMessage):

    def serialize(self, *args, **kwargs):
        soap = ElementMaker(namespace=NSMAP['soap-env'], nsmap=NSMAP)
        body = header = headerfault = None

        header_value = kwargs.pop('_soapheader', None)

        if self.body:
            body_obj = self.body
            body_value = body_obj(*args, **kwargs)
            body = soap.Body()
            body_obj.render(body, body_value)

        if self.header:
            header_obj = self.header
            header_value = header_obj(**header_value)
            header = soap.Header()
            header_obj.render(header, header_value)

        headerfault = None
        return body, header, headerfault

    def deserialize(self, node):
        result = []
        for element in self.abstract.parts.values():
            elm = node.find(element.qname)
            assert elm is not None
            result.append(element.parse(elm))
        if len(result) > 1:
            return tuple(result)
        return result[0]


class Operation(object):
    """Concrete operation

    Contains references to the concrete messages

    """
    def __init__(self, name, abstract_operation):
        self.name = name
        self.abstract = abstract_operation
        self.soapaction = None
        self.style = None
        self.input = None
        self.output = None
        self.fault = None

    def __repr__(self):
        return '<%s(name=%r, style=%r)>' % (
            self.__class__.__name__, self.name.text, self.style)

    def __unicode__(self):
        return '%s(%s)' % (self.name, self.input.signature())

    def create(self, *args, **kwargs):
        return self.input.serialize(*args, **kwargs)

    def process_reply(self, envelope):
        node = envelope.find('soap-env:Body', namespaces=NSMAP)
        return self.output.deserialize(node)

    @classmethod
    def parse(cls, wsdl, xmlelement, binding):
        """

        Example::

            <operation name="GetLastTradePrice">
              <soap:operation soapAction="http://example.com/GetLastTradePrice"/>
              <input>
                <soap:body use="literal"/>
              </input>
              <output>
                <soap:body use="literal"/>
              </output>
            </operation>

        """
        localname = xmlelement.get('name')

        for namespace in wsdl.namespaces:
            name = etree.QName(namespace, localname)
            if name in binding.port_type.operations:
                abstract_operation = binding.port_type.operations[name]
                break
        else:
            raise ValueError("Operation not found")

        # The soap:operation element is required for soap/http bindings
        # and may be omitted for other bindings.
        soap_node = get_soap_node(xmlelement, 'operation')
        action = None
        if soap_node is not None:
            action = soap_node.get('soapAction')
            style = soap_node.get('style', binding.default_style)
        else:
            style = binding.default_style

        obj = cls(name, abstract_operation)
        obj.soapaction = action
        obj.style = style

        for type_ in 'input', 'output', 'fault':
            type_node = xmlelement.find(QName(NSMAP['wsdl'], type_))
            if type_node is None:
                continue

            if style == 'rpc':
                message_class = RpcMessage
            else:
                message_class = DocumentMessage

            abstract = getattr(abstract_operation, type_)
            msg = message_class.parse(wsdl, type_node, abstract, obj)
            setattr(obj, type_, msg)

        return obj


class Port(object):
    def __init__(self, name, binding, location):
        self.name = name
        self.binding = binding
        self.location = location

    def __repr__(self):
        return '<%s(name=%r, binding=%r, location=%r)>' % (
            self.__class__.__name__, self.name, self.binding, self.location)

    def __unicode__(self):
        return 'Port: %s' % self.name

    def send(self, transport, operation, args, kwargs):
        return self.binding.send(
            transport, self.location, operation, args, kwargs)

    @classmethod
    def parse(cls, wsdl, xmlelement):
        name = get_qname(xmlelement, 'name', wsdl.target_namespace)
        binding = get_qname(xmlelement, 'binding', wsdl.target_namespace)

        soap_node = get_soap_node(xmlelement, 'address')
        location = soap_node.get('location')
        obj = cls(name, wsdl.bindings[binding], location=location)
        return obj


class Service(object):

    def __init__(self, name):
        self.ports = {}
        self.name = name

    def __unicode__(self):
        return 'Service: %s' % self.name.text

    def __repr__(self):
        return '<%s(name=%r, ports=%r)>' % (
            self.__class__.__name__, self.name.text, self.ports)

    def add_port(self, port):
        self.ports[port.name] = port

    @classmethod
    def parse(cls, wsdl, xmlelement):
        """

        Example::

              <service name="StockQuoteService">
                <documentation>My first service</documentation>
                <port name="StockQuotePort" binding="tns:StockQuoteBinding">
                  <soap:address location="http://example.com/stockquote"/>
                </port>
              </service>

        """
        tns = wsdl.target_namespace
        name = get_qname(xmlelement, 'name', tns, as_text=False)
        obj = cls(name)
        for port_node in xmlelement.findall('wsdl:port', namespaces=NSMAP):
            port = Port.parse(wsdl, port_node)
            obj.add_port(port)

        return obj


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
            doc = parse_xml(response, self.schema_references, transport)
        else:
            with open(filename) as fh:
                doc = parse_xml(fh.read(), self.schema_references, transport)

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

    def dump(self):
        type_instances = self.schema.types
        print 'Types:'
        for type_obj in sorted(type_instances):
            print '%s%s' % (' ' * 4, unicode(type_obj))

        print ''

        for service in self.services.values():
            print unicode(service)
            for port in service.ports.values():
                print ' ' * 4, unicode(port)
                print ' ' * 8, 'Operations:'
                for operation in port.binding.operations.values():
                    print '%s%s' % (' ' * 12, unicode(operation))

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
        """Return a `types.Schema` instance."""
        namespace_sets = [
            {'xsd': 'http://www.w3.org/2001/XMLSchema'},
            {'xsd': 'http://www.w3.org/1999/XMLSchema'},
        ]

        types = doc.find('wsdl:types', namespaces=NSMAP)

        schema_nodes = findall_multiple_ns(types, 'xsd:schema', namespace_sets)
        if not schema_nodes:
            return None

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

        return Schema(
            schema_nodes[0], self.schema_references, self.transport)

    def parse_messages(self, doc):
        result = {}
        for msg_node in doc.findall("wsdl:message", namespaces=NSMAP):
            msg = AbstractMessage.parse(self, msg_node)
            result[msg.name.text] = msg
        return result

    def parse_ports(self, doc):
        result = {}
        for port_node in doc.findall('wsdl:portType', namespaces=NSMAP):
            port_type = PortType.parse(self, port_node)
            result[port_type.name.text] = port_type
        return result

    def parse_binding(self, doc):
        result = {}
        for binding_node in doc.findall('wsdl:binding', namespaces=NSMAP):
            # Detect the binding type
            if SoapBinding.match(binding_node):
                binding = SoapBinding.parse(self, binding_node)
            elif HttpBinding.match(binding_node):
                binding = SoapBinding.parse(self, binding_node)
            result[binding.name.text] = binding
        return result

    def parse_service(self, doc):
        result = {}
        for service_node in doc.findall('wsdl:service', namespaces=NSMAP):
            service = Service.parse(self, service_node)
            result[service.name.text] = service
        return result


def get_soap_node(parent, name):
    for ns in ['soap', 'soap12']:
        node = parent.find('%s:%s' % (ns, name), namespaces=NSMAP)
        if node is not None:
            return node
