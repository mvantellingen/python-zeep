import six
from defusedxml.lxml import fromstring
from lxml import etree

from zeep.exceptions import Fault, TransportError
from zeep.utils import qname_attr
from zeep.wsdl.definitions import Binding, Operation
from zeep.wsdl.messages import DocumentMessage, RpcMessage
from zeep.wsdl.utils import _soap_element


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
        serialized = operation.create(*args, **kwargs)
        return serialized.content

    def send(self, client, options, operation, args, kwargs):
        """Called from the service"""
        operation_obj = self.get(operation)
        if not operation_obj:
            raise ValueError("Operation %r not found" % operation)

        # Create the SOAP envelope
        serialized = operation_obj.create(*args, **kwargs)
        serialized.headers['Content-Type'] = self.content_type

        envelope = serialized.content
        headers = serialized.headers

        # Apply plugins

        # Apply WSSE
        if client.wsse:
            envelope, http_headers = client.wsse.sign(envelope, headers)

        response = client.transport.post(
            options['address'], etree.tostring(envelope), headers)

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
    content_type = 'application/soap+xml; charset=utf-8'


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
            msg = message_class.parse(
                definitions=definitions, xmlelement=node,
                operation=obj, nsmap=nsmap)
            if tag_name == 'fault':
                obj.faults[msg.name] = msg
            else:
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
