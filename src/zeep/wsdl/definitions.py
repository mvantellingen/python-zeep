from collections import OrderedDict, namedtuple

from lxml import etree

from zeep.utils import qname_attr

NSMAP = {
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
}

MessagePart = namedtuple('MessagePart', ['element', 'type'])


class AbstractMessage(object):
    def __init__(self, name):
        self.name = name
        self.parts = OrderedDict()

    def __repr__(self):
        return '<%s(name=%r)>' % (self.__class__.__name__, self.name.text)

    def resolve(self, definitions):
        pass

    def add_part(self, name, element):
        self.parts[name] = element

    def get_part(self, name):
        return self.parts[name]

    @classmethod
    def parse(cls, definitions, xmlelement):
        """
            <definitions .... >
                <message name="nmtoken"> *
                    <part name="nmtoken" element="qname"? type="qname"?/> *
                </message>
            </definitions>
        """
        msg = cls(name=qname_attr(xmlelement, 'name', definitions.target_namespace))

        for part in xmlelement.findall('wsdl:part', namespaces=NSMAP):
            part_name = part.get('name')

            part_element = qname_attr(part, 'element', definitions.target_namespace)
            part_type = qname_attr(part, 'type', definitions.target_namespace)

            if part_element is not None:
                part_element = definitions.schema.get_element(part_element)

            if part_type is not None:
                part_type = definitions.schema.get_type(part_type)

            msg.add_part(part_name, MessagePart(part_element, part_type))
        return msg


class AbstractOperation(object):
    """Abstract operations are defined in the wsdl's portType elements."""

    def __init__(self, name, input=None, output=None, faults=None,
                 parameter_order=None):
        self.name = name
        self.input = input
        self.output = output
        self.faults = faults
        self.parameter_order = parameter_order

    def get(self, type_, name=None):
        if type_ in ('input', 'output'):
            return getattr(self, type_)
        return self.faults[name]

    @classmethod
    def parse(cls, definitions, xmlelement):
        """
            <wsdl:operation name="nmtoken">*
               <wsdl:documentation .... /> ?
               <wsdl:input name="nmtoken"? message="qname">?
                   <wsdl:documentation .... /> ?
               </wsdl:input>
               <wsdl:output name="nmtoken"? message="qname">?
                   <wsdl:documentation .... /> ?
               </wsdl:output>
               <wsdl:fault name="nmtoken" message="qname"> *
                   <wsdl:documentation .... /> ?
               </wsdl:fault>
            </wsdl:operation>
        """
        name = xmlelement.get('name')
        kwargs = {
            'faults': {}
        }

        for msg_node in xmlelement.getchildren():
            tag_name = etree.QName(msg_node.tag).localname
            if tag_name not in ('input', 'output', 'fault'):
                continue

            param_msg = qname_attr(msg_node, 'message', definitions.target_namespace)
            param_name = msg_node.get('name')
            if tag_name in ('input', 'output'):
                kwargs[tag_name] = definitions.messages[param_msg.text]
            else:
                kwargs['faults'][param_name] = definitions.messages[param_msg.text]

        kwargs['name'] = name
        kwargs['parameter_order'] = xmlelement.get('parameterOrder')
        return cls(**kwargs)


class PortType(object):
    def __init__(self, name, operations):
        self.name = name
        self.operations = operations

    def __repr__(self):
        return '<%s(name=%r)>' % (
            self.__class__.__name__, self.name.text)

    def resolve(self, definitions):
        pass

    @classmethod
    def parse(cls, definitions, xmlelement):
        """
            <wsdl:definitions .... >
                <wsdl:portType name="nmtoken">
                    <wsdl:operation name="nmtoken" .... /> *
                </wsdl:portType>
            </wsdl:definitions>

        """
        name = qname_attr(xmlelement, 'name', definitions.target_namespace)
        operations = {}
        for elm in xmlelement.findall('wsdl:operation', namespaces=NSMAP):
            operation = AbstractOperation.parse(definitions, elm)
            operations[operation.name] = operation
        return cls(name, operations)


class Binding(object):
    """Base class for the various bindings (SoapBinding / HttpBinding)

        Binding
           |
           +-> Operation
                   |
                   +-> ConcreteMessage
                             |
                             +-> AbstractMessage

    """
    def __init__(self, wsdl, name, port_name):
        self.name = name
        self.port_name = port_name
        self.port_type = None
        self.wsdl = wsdl
        self._operations = {}

    def resolve(self, definitions):
        self.port_type = definitions.port_types[self.port_name.text]
        for operation in self._operations.values():
            operation.resolve(definitions)

    def _operation_add(self, operation):
        # XXX: operation name is not unique
        self._operations[operation.name] = operation

    def __repr__(self):
        return '<%s(name=%r, port_type=%r)>' % (
            self.__class__.__name__, self.name.text, self.port_type)

    def get(self, name):
        return self._operations.get(name)

    @classmethod
    def match(cls, node):
        raise NotImplementedError()

    @classmethod
    def parse(cls, definitions, xmlelement):
        raise NotImplementedError()


class ConcreteMessage(object):
    def __init__(self, wsdl, name, operation):
        self.wsdl = wsdl
        self.namespace = {}
        self.operation = operation
        self.name = name

    def create(self, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def parse(cls, wsdl, xmlelement, abstract_message, operation):
        raise NotImplementedError()

    def signature(self, as_output=False):
        if as_output:
            return self.body.type.name
        return self.body.type.signature()


class Operation(object):
    """Concrete operation

    Contains references to the concrete messages

    """
    def __init__(self, name, binding):
        self.name = name
        self.binding = binding
        self.abstract = None
        self.style = None
        self.input = None
        self.output = None
        self.faults = {}

    def resolve(self, definitions):
        self.abstract = self.binding.port_type.operations[self.name]

    def __repr__(self):
        return '<%s(name=%r, style=%r)>' % (
            self.__class__.__name__, self.name, self.style)

    def __unicode__(self):
        if not self.input:
            return '%s(missing input message)' % (self.name)

        retval = '%s(%s)' % (self.name, self.input.signature())
        if self.output:
            retval += ' -> %s' % (self.output.signature(as_output=True))
        return retval

    def create(self, *args, **kwargs):
        return self.input.serialize(*args, **kwargs)

    def process_reply(self, envelope):
        raise NotImplementedError()

    @classmethod
    def parse(cls, wsdl, xmlelement, binding):
        """
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
        """
        raise NotImplementedError()


class Port(object):
    def __init__(self, name, binding_name, xmlelement):
        self.name = name
        self._resolve_context = {
            'binding_name': binding_name,
            'xmlelement': xmlelement,
        }

        # Set during resolve()
        self.binding = None
        self.binding_options = None

    def __repr__(self):
        return '<%s(name=%r, binding=%r, %r)>' % (
            self.__class__.__name__, self.name, self.binding,
            self.binding_options)

    def __unicode__(self):
        return 'Port: %s' % self.name

    def send(self, client, operation, args, kwargs):
        return self.binding.send(
            client, self.binding_options, operation, args, kwargs)

    @classmethod
    def parse(cls, wsdl, xmlelement):
        """
            <wsdl:port name="nmtoken" binding="qname"> *
               <wsdl:documentation .... /> ?
               <-- extensibility element -->
            </wsdl:port>

        """
        name = qname_attr(xmlelement, 'name', wsdl.target_namespace)
        binding_name = qname_attr(xmlelement, 'binding', wsdl.target_namespace)
        return cls(name.text, binding_name=binding_name, xmlelement=xmlelement)

    def resolve(self, definitions):
        if self._resolve_context is None:
            return

        binding = definitions.bindings.get(
            self._resolve_context['binding_name'].text)
        if not binding:
            return False

        self.binding = binding
        self.binding_options = binding.process_service_port(
            self._resolve_context['xmlelement'])
        self._resolve_context = None
        return True


class Service(object):

    def __init__(self, name):
        self.ports = OrderedDict()
        self.name = name
        self._is_resolved = False

    def __unicode__(self):
        return 'Service: %s' % self.name.text

    def __repr__(self):
        return '<%s(name=%r, ports=%r)>' % (
            self.__class__.__name__, self.name.text, self.ports)

    def resolve(self, definitions):
        if self._is_resolved:
            return

        unresolved = []
        for name, port in self.ports.items():
            is_resolved = port.resolve(definitions)
            if not is_resolved:
                unresolved.append(name)

        # Remove unresolved bindings (http etc)
        for name in unresolved:
            del self.ports[name]

        self._is_resolved = True

    def add_port(self, port):
        self.ports[port.name] = port

    @classmethod
    def parse(cls, definitions, xmlelement):
        """

        Syntax::

            <wsdl:service name="nmtoken"> *
                <wsdl:documentation .... />?
                <wsdl:port name="nmtoken" binding="qname"> *
                   <wsdl:documentation .... /> ?
                   <-- extensibility element -->
                </wsdl:port>
                <-- extensibility element -->
            </wsdl:service>

        Example::

              <service name="StockQuoteService">
                <documentation>My first service</documentation>
                <port name="StockQuotePort" binding="tns:StockQuoteBinding">
                  <soap:address location="http://example.com/stockquote"/>
                </port>
              </service>

        """
        name = qname_attr(xmlelement, 'name', definitions.target_namespace)
        obj = cls(name)
        for port_node in xmlelement.findall('wsdl:port', namespaces=NSMAP):
            port = Port.parse(definitions, port_node)
            if port:
                obj.add_port(port)

        return obj
