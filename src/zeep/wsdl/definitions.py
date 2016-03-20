from collections import OrderedDict

from zeep import xsd
from zeep.utils import get_qname

NSMAP = {
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'soap12': 'http://schemas.xmlsoap.org/wsdl/soap12/',
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


class Operation(object):
    """Concrete operation

    Contains references to the concrete messages

    """
    def __init__(self, name, abstract_operation):
        self.name = name
        self.abstract = abstract_operation
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
        raise NotImplementedError()

    @classmethod
    def parse(cls, wsdl, xmlelement, binding):
        raise NotImplementedError()


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


def get_soap_node(parent, name):
    for ns in ['soap', 'soap12']:
        node = parent.find('%s:%s' % (ns, name), namespaces=NSMAP)
        if node is not None:
            return node
