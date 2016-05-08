import six
from defusedxml.lxml import fromstring
from lxml import etree
from lxml.builder import ElementMaker

from zeep import xsd
from zeep.exceptions import Fault, TransportError
from zeep.utils import qname_attr
from zeep.wsdl.definitions import Binding, ConcreteMessage, Operation
from zeep.xsd import Element


class SoapBinding(Binding):
    """Soap 1.1/1.2 binding"""

    def __init__(self, wsdl, name, port_name, transport, default_style):
        super(SoapBinding, self).__init__(wsdl, name, port_name)
        self.transport = transport
        self.default_style = default_style

    @classmethod
    def match(cls, node):
        soap_node = node.find('soap:binding', namespaces=cls.nsmap)
        return soap_node is not None

    def create_message(self, operation, *args, **kwargs):
        """Create the XML document to send to the server.

        Note that this generates the soap envelope without the wsse applied.

        """
        if isinstance(operation, six.string_types):
            operation = self.get(operation)
            if not operation:
                raise ValueError("Operation not found")

        nsmap = self.nsmap.copy()
        nsmap.update(self.wsdl.schema._prefix_map)

        body, header, headerfault = operation.create(*args, **kwargs)
        soap = ElementMaker(namespace=self.nsmap['soap-env'], nsmap=nsmap)

        envelope = soap.Envelope()
        if header is not None:
            envelope.append(header)
        if body is not None:
            envelope.append(body)

        return envelope

    def send(self, client, options, operation, args, kwargs):
        """Called from the service"""
        operation_obj = self.get(operation)
        if not operation_obj:
            raise ValueError("Operation %r not found" % operation)

        # Create the SOAP envelope
        envelope = self.create_message(operation_obj, *args, **kwargs)
        http_headers = {
            'Content-Type': self.content_type,
            'SOAPAction': operation_obj.soapaction,
        }

        # Apply plugins

        # Apply WSSE
        if client.wsse:
            envelope, http_headers = client.wsse.sign(envelope, http_headers)

        response = client.transport.post(
            options['address'], etree.tostring(envelope), http_headers)

        return self.process_reply(client, operation_obj, response)

    def process_reply(self, client, operation, response):
        """Process the XML reply from the server.

        """
        if response.status_code != 200 and not response.content:
            raise TransportError(
                u'Server returned HTTP status %d (no content available)'
                % response.status_code)

        try:
            doc = fromstring(response.content)
        except etree.XMLSyntaxError:
            raise TransportError(
                u'Server returned HTTP status %d (%s)'
                % (response.status_code, response.content))

        if client.wsse:
            client.wsse.verify(doc)

        if response.status_code != 200:
            return self.process_error(doc)

        return operation.process_reply(doc)

    def process_error(self, doc):
        fault_node = doc.find(
            'soap-env:Body/soap-env:Fault', namespaces=self.nsmap)

        if fault_node is None:
            raise Fault(
                message='Unknown fault occured',
                code=None,
                actor=None,
                detail=etree.tostring(doc))

        def get_text(name):
            child = fault_node.find(name)
            if child is not None:
                return child.text

        raise Fault(
            message=get_text('faultstring'),
            code=get_text('faultcode'),
            actor=get_text('faultactor'),
            detail=fault_node.find('detail'))

    def process_service_port(self, xmlelement):
        address_node = _soap_element(xmlelement, 'address')
        return {
            'address': address_node.get('location')
        }

    @classmethod
    def parse(cls, definitions, xmlelement):
        """
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
        """
        name = qname_attr(xmlelement, 'name', definitions.target_namespace)
        port_name = qname_attr(xmlelement, 'type', definitions.target_namespace)

        # The soap:binding element contains the transport method and
        # default style attribute for the operations.
        soap_node = _soap_element(xmlelement, 'binding')
        transport = soap_node.get('transport')
        if transport != 'http://schemas.xmlsoap.org/soap/http':
            raise NotImplementedError("Only soap/http is supported for now")
        default_style = soap_node.get('style', 'document')

        obj = cls(definitions.wsdl, name, port_name, transport, default_style)
        for node in xmlelement.findall('wsdl:operation', namespaces=cls.nsmap):
            operation = SoapOperation.parse(definitions, node, obj, nsmap=cls.nsmap)
            obj._operation_add(operation)
        return obj


class Soap11Binding(SoapBinding):
    nsmap = {
        'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
        'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
        'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
    }
    content_type = 'text/xml; charset=utf-8'


class Soap12Binding(SoapBinding):
    nsmap = {
        'soap': 'http://schemas.xmlsoap.org/wsdl/soap12/',
        'soap-env': 'http://www.w3.org/2003/05/soap-envelope',
        'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
    }
    content_type = 'application/xml+soap; charset=utf-8'


class SoapOperation(Operation):

    def __init__(self, name, binding, nsmap, soapaction, style):
        super(SoapOperation, self).__init__(name, binding)
        self.nsmap = nsmap
        self.soapaction = soapaction
        self.style = style

    def process_reply(self, envelope):
        node = envelope.find('soap-env:Body', namespaces=self.nsmap)
        return self.output.deserialize(node)

    @classmethod
    def parse(cls, definitions, xmlelement, binding, nsmap):
        """

            <wsdl:operation name="nmtoken"> *
                <soap:operation soapAction="uri"? style="rpc|document"?>?
                <wsdl:input name="nmtoken"? > ?
                    <soap:body use="literal"/>
               </wsdl:input>
               <wsdl:output name="nmtoken"? > ?
                    <-- extensibility element (4) --> *
               </wsdl:output>
               <wsdl:fault name="nmtoken"> *
                    <-- extensibility element (5) --> *
               </wsdl:fault>
            </wsdl:operation>

        Example::

            <wsdl:operation name="GetLastTradePrice">
              <soap:operation soapAction="http://example.com/GetLastTradePrice"/>
              <wsdl:input>
                <soap:body use="literal"/>
              </wsdl:input>
              <wsdl:output>
              </wsdl:output>
              <wsdl:fault name="dataFault">
                <soap:fault name="dataFault" use="literal"/>
              </wsdl:fault>
            </operation>

        """
        name = xmlelement.get('name')

        # The soap:operation element is required for soap/http bindings
        # and may be omitted for other bindings.
        soap_node = _soap_element(xmlelement, 'operation')
        action = None
        if soap_node is not None:
            action = soap_node.get('soapAction')
            style = soap_node.get('style', binding.default_style)
        else:
            style = binding.default_style

        obj = cls(name, binding, nsmap, action, style)

        if style == 'rpc':
            message_class = RpcMessage
        else:
            message_class = DocumentMessage

        for node in xmlelement.getchildren():
            tag_name = etree.QName(node.tag).localname
            if tag_name not in ('input', 'output', 'fault'):
                continue
            name = node.get('name')

            if tag_name == 'fault':
                msg = message_class.parse(
                    definitions, node, name, tag_name, obj, nsmap)
                obj.faults[msg.name] = msg

            else:
                msg = message_class.parse(
                    definitions, node, name, tag_name, obj, nsmap)
                setattr(obj, tag_name, msg)

        return obj

    def resolve(self, definitions):
        super(SoapOperation, self).resolve(definitions)
        for name, fault in self.faults.items():
            fault.resolve(definitions, self.abstract.faults[name])

        if self.output:
            self.output.resolve(definitions, self.abstract.output)
        if self.input:
            self.input.resolve(definitions, self.abstract.input)


class SoapMessage(ConcreteMessage):

    def __init__(self, wsdl, name, operation, nsmap):
        super(SoapMessage, self).__init__(wsdl, name, operation)
        self.nsmap = nsmap
        self.abstract = None  # Set during resolve()
        self.body = None
        self.header = None
        self.headerfault = None

    @classmethod
    def parse(cls, definitions, xmlelement, name, tag_name, operation, nsmap):
        """
        Example::

              <output>
                <soap:body use="literal"/>
              </output>

        """
        obj = cls(definitions.wsdl, name, operation, nsmap=nsmap)

        tns = definitions.target_namespace
        body = _soap_element(xmlelement, 'body')
        header = _soap_element(xmlelement, 'header')
        headerfault = _soap_element(xmlelement, 'headerfault')

        obj._info = {
            'body': {}, 'header': {}, 'headerfault': {}
        }

        if body is not None:
            obj._info['body'] = {
                'part': body.get('part'),
                'use': body.get('use', 'literal'),
                'encodingStyle': body.get('encodingStyle'),
                'namespace': body.get('namespace'),
            }

        if header is not None:
            obj._info['header'] = {
                'message': qname_attr(header, 'message', tns),
                'part': header.get('part'),
                'use': header.get('use', 'literal'),
                'encodingStyle': header.get('encodingStyle'),
                'namespace': header.get('namespace'),
            }

        if headerfault is not None:
            obj._info['headerfault'] = {
                'message': qname_attr(headerfault, 'message', tns),
                'part': headerfault.get('part'),
                'use': headerfault.get('use', 'literal'),
                'encodingStyle': headerfault.get('encodingStyle'),
                'namespace': headerfault.get('namespace'),
            }

        obj.namespace = {
            'body': obj._info['body'].get('namespace'),
            'header': obj._info['header'].get('namespace'),
            'headerfault': obj._info['headerfault'].get('namespace'),
        }
        return obj

    def resolve(self, definitions, abstract_message):
        self.abstract = abstract_message

        header_info = self._info['header']
        headerfault_info = self._info['headerfault']
        body_info = self._info['body']
        part_names = list(abstract_message.parts.keys())

        if header_info:
            part_name = header_info['part']
            if header_info['message']:
                msg = definitions.messages[header_info['message'].text]
                self.header = msg.parts[part_name].element
                if msg == abstract_message:
                    part_names.remove(part_name)
            else:
                part_names.remove(part_name)
                self.header = abstract_message.parts[part_name].element
        else:
            self.header = None

        if headerfault_info:
            part_name = headerfault_info['part']
            part_names.remove(part_name)
            self.headerfault = abstract_message.parts[part_name].element
        else:
            self.headerfault = None

        if body_info:
            part_name = body_info['part'] or part_names[0]
            part_names.remove(part_name)
            self.body = abstract_message.parts[part_name].element


class RpcMessage(SoapMessage):
    def serialize(self, *args, **kwargs):
        soap = ElementMaker(namespace=self.nsmap['soap-env'], nsmap=self.nsmap)
        tag_name = etree.QName(
            self.namespace['body'], self.abstract.name.localname)

        body = soap.Body()
        operation = xsd.Element(tag_name, xsd.ComplexType(children=[
            xsd.Element(etree.QName(name), message.type)
            for name, message in self.abstract.parts.items()
        ]))

        operation_value = operation(*args, **kwargs)
        operation.render(body, operation_value)

        return body, None, None

    def deserialize(self, node):
        tag_name = etree.QName(
            self.namespace['body'], self.abstract.name.localname)

        # FIXME
        result = xsd.Element(tag_name, xsd.ComplexType(children=[
            xsd.Element(etree.QName(etree.QName(name).localname), message.type)
            for name, message in self.abstract.parts.items()
        ]))

        value = node.find(result.qname)
        result = result.parse(value)

        result = [
            getattr(result, field.name) for field in result._xsd_type._children
        ]
        if len(result) > 1:
            return tuple(result)
        return result[0]

    def signature(self):
        # if self.operation.abstract.parameter_order:
        #     self.operation.abstract.parameter_order.split()
        return self.abstract.parts.keys()


class DocumentMessage(SoapMessage):

    def serialize(self, *args, **kwargs):
        soap = ElementMaker(namespace=self.nsmap['soap-env'], nsmap=self.nsmap)
        body = header = headerfault = None
        header_value = kwargs.pop('_soapheader', None)

        if self.body:
            body_obj = self.body
            body_value = body_obj(*args, **kwargs)
            body = soap.Body()
            body_obj.render(body, body_value)

        if self.header:
            header_obj = self.header
            if header_value is None:
                header_value = header_obj()
            elif not isinstance(header_value, Element):
                header_value = header_obj(**header_value)
            header = soap.Header()
            header_obj.render(header, header_value)

        headerfault = None
        return body, header, headerfault

    def deserialize(self, node):
        result = []
        for part in self.abstract.parts.values():
            elm = node.find(part.element.qname)
            assert elm is not None, '%s not found' % part.element.qname
            result.append(part.element.parse(elm))

        if len(result) > 1:
            return tuple(result)

        # FIXME (not so sure about this): If the response object has only one
        # property then return that property
        item = result[0]
        if len(item._xsd_type.properties()) == 1:
            return getattr(item, item._xsd_type.properties()[0].name)
        return item

    def signature(self, as_output=False):
        if as_output:
            if len(self.body.type.properties()) == 1:
                return self.body.type.properties()[0].type.name

            return self.body.type.name
        return self.body.type.signature()


def _soap_element(xmlelement, key):
    """So soap1.1 and 1.2 namespaces can be mixed HAH!"""
    namespaces = [
        'http://schemas.xmlsoap.org/wsdl/soap/',
        'http://schemas.xmlsoap.org/wsdl/soap12/',
    ]

    for ns in namespaces:
        retval = xmlelement.find('soap:%s' % key, namespaces={'soap': ns})
        if retval is not None:
            return retval
