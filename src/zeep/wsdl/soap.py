from lxml import etree

from zeep import plugins, wsa
from zeep.exceptions import Fault, TransportError, XMLSyntaxError
from zeep.parser import parse_xml
from zeep.utils import qname_attr
from zeep.wsdl.definitions import Binding, Operation
from zeep.wsdl.messages import DocumentMessage, RpcMessage
from zeep.wsdl.utils import etree_to_string


class SoapBinding(Binding):
    """Soap 1.1/1.2 binding"""

    def __init__(self, wsdl, name, port_name, transport, default_style):
        """The SoapBinding is the base class for the Soap11Binding and
        Soap12Binding.

        :param wsdl:
        :type wsdl:
        :param name:
        :type name: string
        :param port_name:
        :type port_name: string
        :param transport:
        :type transport: zeep.transports.Transport
        :param default_style:

        """
        super(SoapBinding, self).__init__(wsdl, name, port_name)
        self.transport = transport
        self.default_style = default_style

    @classmethod
    def match(cls, node):
        """Check if this binding instance should be used to parse the given
        node.

        :param node: The node to match against
        :type node: lxml.etree._Element

        """
        soap_node = node.find('soap:binding', namespaces=cls.nsmap)
        return soap_node is not None

    def create_message(self, operation, *args, **kwargs):
        envelope, http_headers = self._create(operation, args, kwargs)
        return envelope

    def _create(self, operation, args, kwargs, client=None, options=None):
        """Create the XML document to send to the server.

        Note that this generates the soap envelope without the wsse applied.

        """
        operation_obj = self.get(operation)
        if not operation_obj:
            raise ValueError("Operation %r not found" % operation)

        # Create the SOAP envelope
        serialized = operation_obj.create(*args, **kwargs)
        serialized.headers['Content-Type'] = self.content_type

        envelope = serialized.content
        http_headers = serialized.headers

        # Apply ws-addressing
        if client:
            if not options:
                options = client.service._binding_options

            if operation_obj.abstract.input_message.wsa_action:
                envelope, http_headers = wsa.WsAddressingPlugin().egress(
                    envelope, http_headers, operation_obj, options)

            # Apply plugins
            envelope, http_headers = plugins.apply_egress(
                client, envelope, http_headers, operation_obj, options)

            # Apply WSSE
            if client.wsse:
                envelope, http_headers = client.wsse.sign(envelope, http_headers)
        return envelope, http_headers

    def send(self, client, options, operation, args, kwargs):
        """Called from the service

        :param client: The client with which the operation was called
        :type client: zeep.client.Client
        :param options: The binding options
        :type options: dict
        :param operation: The operation object from which this is a reply
        :type operation: zeep.wsdl.definitions.Operation
        :param args: The *args to pass to the operation
        :type args: tuple
        :param kwargs: The **kwargs to pass to the operation
        :type kwargs: dict

        """
        envelope, http_headers = self._create(
            operation, args, kwargs,
            client=client,
            options=options)

        response = client.transport.post_xml(
            options['address'], envelope, http_headers)

        operation_obj = self.get(operation)
        return self.process_reply(client, operation_obj, response)

    def process_reply(self, client, operation, response):
        """Process the XML reply from the server.

        :param client: The client with which the operation was called
        :type client: zeep.client.Client
        :param operation: The operation object from which this is a reply
        :type operation: zeep.wsdl.definitions.Operation
        :param response: The response object returned by the remote server
        :type response: requests.Response

        """
        if response.status_code != 200 and not response.content:
            raise TransportError(
                u'Server returned HTTP status %d (no content available)'
                % response.status_code)

        try:
            doc = parse_xml(response.content, recover=True)
        except XMLSyntaxError:
            raise TransportError(
                u'Server returned HTTP status %d (%s)'
                % (response.status_code, response.content))

        if client.wsse:
            client.wsse.verify(doc)

        doc, http_headers = plugins.apply_ingress(
            client, doc, response.headers, operation)

        if response.status_code != 200:
            return self.process_error(doc)

        return operation.process_reply(doc)

    def process_error(self, doc):
        raise NotImplementedError

    def process_service_port(self, xmlelement):
        address_node = xmlelement.find('soap:address', namespaces=self.nsmap)
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
        soap_node = xmlelement.find('soap:binding', namespaces=cls.nsmap)
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

    def process_error(self, doc):
        fault_node = doc.find(
            'soap-env:Body/soap-env:Fault', namespaces=self.nsmap)

        if fault_node is None:
            raise Fault(
                message='Unknown fault occured',
                code=None,
                actor=None,
                detail=etree_to_string(doc))

        def get_text(name):
            child = fault_node.find(name)
            if child is not None:
                return child.text

        raise Fault(
            message=get_text('faultstring'),
            code=get_text('faultcode'),
            actor=get_text('faultactor'),
            detail=fault_node.find('detail'))


class Soap12Binding(SoapBinding):
    nsmap = {
        'soap': 'http://schemas.xmlsoap.org/wsdl/soap12/',
        'soap-env': 'http://www.w3.org/2003/05/soap-envelope',
        'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
    }
    content_type = 'application/soap+xml; charset=utf-8'

    def process_error(self, doc):
        fault_node = doc.find(
            'soap-env:Body/soap-env:Fault', namespaces=self.nsmap)

        if fault_node is None:
            raise Fault(
                message='Unknown fault occured',
                code=None,
                actor=None,
                detail=etree_to_string(doc))

        def get_text(name):
            child = fault_node.find(name)
            if child is not None:
                return child.text

        message = fault_node.findtext('soap-env:Reason/soap-env:Text', namespaces=self.nsmap)
        code = fault_node.findtext('soap-env:Code/soap-env:Value', namespaces=self.nsmap)
        raise Fault(
            message=message,
            code=code,
            actor=None,
            detail=fault_node.find('Detail'))


class SoapOperation(Operation):
    """Represent's an operation within a specific binding."""

    def __init__(self, name, binding, nsmap, soapaction, style):
        super(SoapOperation, self).__init__(name, binding)
        self.nsmap = nsmap
        self.soapaction = soapaction
        self.style = style

    def process_reply(self, envelope):
        envelope_qname = etree.QName(self.nsmap['soap-env'], 'Envelope')
        if envelope.tag != envelope_qname:
            raise XMLSyntaxError((
                "The XML returned by the server does not contain a valid " +
                "{%s}Envelope root element. The root element found is %s "
            ) % (envelope_qname.namespace, envelope.tag))

        body = envelope.find('soap-env:Body', namespaces=self.nsmap)
        assert body is not None, "No {%s}Body element found" % (self.nsmap['soap-env'])
        return self.output.deserialize(body)

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
        soap_node = xmlelement.find('soap:operation', namespaces=binding.nsmap)
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
            msg = message_class.parse(
                definitions=definitions, xmlelement=node,
                operation=obj, nsmap=nsmap, type=tag_name)
            if tag_name == 'fault':
                obj.faults[msg.name] = msg
            else:
                setattr(obj, tag_name, msg)

        return obj

    def resolve(self, definitions):
        super(SoapOperation, self).resolve(definitions)
        for name, fault in self.faults.items():
            if name in self.abstract.fault_messages:
                fault.resolve(definitions, self.abstract.fault_messages[name])

        if self.output:
            self.output.resolve(definitions, self.abstract.output_message)
        if self.input:
            self.input.resolve(definitions, self.abstract.input_message)
