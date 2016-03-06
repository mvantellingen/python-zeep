import pprint
from collections import namedtuple

from lxml.builder import ElementMaker
import requests
from lxml.etree import QName
from lxml import etree

from zeep import xsd
from zeep.parser import parse_xml
from zeep.types import Schema
from zeep.utils import findall_multiple_ns, get_qname, parse_qname

NSMAP = {
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'soap12': 'http://schemas.xmlsoap.org/wsdl/soap12/',
    'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
}


AbstractOperation = namedtuple(
    'AbstractOperation', ['input', 'output', 'fault'])


class AbstractMessage(object):
    def __init__(self, name):
        self.name = name
        self.parts = {}

    def __repr__(self):
        return '<%s(name=%r)>' % (
            self.__class__.__name__, self.name.text)

    def add_part(self, name, element):
        self.parts[name] = element

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
                part_type = wsdl.types.get_element(part_element)
            else:
                part_type = get_qname(part, 'type', wsdl.target_namespace)
                part_type = wsdl.types.get_type(part_type)
                part_type = xsd.Element(part_name, type_=part_type())
            msg.add_part(part_name, part_type)
        return msg


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
            name = get_qname(elm, 'name', wsdl.target_namespace, as_text=False)
            messages = {}

            for type_ in 'input', 'output', 'fault':
                msg_node = elm.find('wsdl:%s' % type_, namespaces=NSMAP)
                if msg_node is None:
                    continue
                key = '%s_message' % type_
                message_name = get_qname(
                    msg_node, 'message', wsdl.target_namespace)
                messages[key] = wsdl.messages[message_name]
            obj.add_operation(name, **messages)
        return obj

    def add_operation(self, name, input_message=None, output_message=None,
                      fault_message=None):
        self.operations[name.text] = AbstractOperation(
            input_message, output_message, fault_message)

    def get_operation(self, name):
        return self.operations[name.text]


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
        print etree.tostring(envelope, pretty_print=True)
        response = transport.send(
            address, etree.tostring(envelope), http_headers)
        return


    def get(self, name):
        return self.operations[name]

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


class ConcreteMessage(object):
    def __init__(self, wsdl, abstract):
        self.abstract = abstract
        self.wsdl = wsdl
        self.namespace = {}

    def create(self, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def parse(cls, wsdl, xmlelement, abstract):
        """
        Example::

              <output>
                <soap:body use="literal"/>
              </output>

        """
        obj = cls(wsdl, abstract)

        body = get_soap_node(xmlelement, 'body')
        header = get_soap_node(xmlelement, 'header')
        headerfault = get_soap_node(xmlelement, 'headerfault')

        obj.namespace = {
            'body': body.get('namespace'),
            'header': body.get('header'),
            'headerfault': body.get('headerfault'),
        }

        obj.body = abstract.parts.values()[0]
        obj.header = None
        obj.headerfault = None
        return obj

class RpcMessage(ConcreteMessage):
    def create(self, *args, **kwargs):
        soap = ElementMaker(namespace=NSMAP['soap-env'], nsmap=NSMAP)

        body = soap.Body()
        method = etree.SubElement(
            body,
            etree.QName(self.namespace['body'], self.abstract.name.localname))
        for key, value in kwargs.iteritems():
            key = parse_qname(key, self.wsdl.nsmap, self.wsdl.target_namespace)
            obj = self.abstract.get_part(key)
            obj.render(method, value)
        return body, None, None



class DocumentMessage(ConcreteMessage):

    def create(self, *args, **kwargs):
        soap = ElementMaker(namespace=NSMAP['soap-env'], nsmap=NSMAP)
        body = header = headerfault = None

        if self.body:
            body_obj = self.body
            body_value = body_obj(*args, **kwargs)
            body = soap.Body()
            body_obj.render(body, body_value)

        if self.header:
            header = self.header

        headerfault = None

        return body, header, headerfault


class Operation(object):

    def __init__(self, name, abstract_operation):
        self.name = name
        self.abstract = abstract_operation
        self.soapaction = None
        self.style = None
        self.protocol = {}
        self.input = None
        self.output = None
        self.fault = None

    def __repr__(self):
        return '<%s(name=%r, style=%r)>' % (
            self.__class__.__name__, self.name.text, self.style)

    def create(self, *args, **kwargs):
        body = header = headerfault = None
        soap = ElementMaker(namespace=NSMAP['soap-env'], nsmap=NSMAP)
        return self.input.create(*args, **kwargs)


    def protocol_info(self, type_, use, namespace):
        self.protocol[type_] = {
            'namespace': namespace,
            'use': use
        }

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
        name = get_qname(
            xmlelement, 'name', wsdl.target_namespace, as_text=False)
        abstract_operation = binding.port_type.get_operation(name)

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
            msg = message_class.parse(wsdl, type_node, abstract)
            setattr(obj, type_, msg)

        return obj


class Port(object):
    def __init__(self, name, binding, location):
        self.name = name
        self.binding = binding
        self.location = location

    def get_operation(self, name):
        return self.binding.get(name)

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
    def __init__(self, filename):
        self.types = {}
        self.schema_references = {}

        if filename.startswith(('http://', 'https://')):
            response = requests.get(filename)
            doc = parse_xml(response.content, self.schema_references)
        else:
            with open(filename) as fh:
                doc = parse_xml(fh.read(), self.schema_references)

        self.nsmap = doc.nsmap
        self.target_namespace = doc.get('targetNamespace')
        self.types = self.parse_types(doc)
        self.messages = self.parse_messages(doc)
        self.ports = self.parse_ports(doc)
        self.bindings = self.parse_binding(doc)
        self.services = self.parse_service(doc)

    def dump(self):
        print self.services
        return
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
        namespace_sets = [
            {'xsd': 'http://www.w3.org/2001/XMLSchema'},
            {'xsd': 'http://www.w3.org/1999/XMLSchema'},
        ]

        types = doc.find('wsdl:types', namespaces=NSMAP)

        schema_nodes = findall_multiple_ns(types, 'xsd:schema', namespace_sets)
        if not schema_nodes:
            return Schema()

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

        return Schema(schema_nodes[0], self.schema_references)

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
        findall = lambda node, name: node.findall(name, namespaces=NSMAP)
        tns = doc.get('targetNamespace')
        bindings = {}

        for binding_node in findall(doc, 'wsdl:binding'):
            binding = Binding.parse(self, binding_node)
            bindings[binding.name.text] = binding

        return bindings

    def parse_service(self, doc):
        findall = lambda node, name: node.findall(name, namespaces=NSMAP)
        tns = doc.get('targetNamespace')

        result = {}
        for service_node in findall(doc, 'wsdl:service'):
            service = Service.parse(self, service_node)
            result[service.name.text] = service

        return result


def get_soap_node(parent, name):
    for ns in ['soap', 'soap12']:
        node = parent.find('%s:%s' % (ns, name), namespaces=NSMAP)
        if node is not None:
            return node
