
from lxml import etree
from lxml.builder import ElementMaker

from zeep.utils import get_qname, parse_qname, process_signature
from zeep.wsdl.definitions import Binding, ConcreteMessage, Operation

NSMAP = {
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'soap12': 'http://schemas.xmlsoap.org/wsdl/soap12/',
    'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
}


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
        name = get_qname(
            xmlelement, 'name', wsdl.target_namespace, as_text=False)
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
            operation = SoapOperation.parse(wsdl, node, obj)

            # XXX: operation name is not unique
            obj.operations[operation.name.text] = operation

        return obj


class SoapOperation(Operation):

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
            type_node = xmlelement.find(etree.QName(NSMAP['wsdl'], type_))
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


def get_soap_node(parent, name):
    for ns in ['soap', 'soap12']:
        node = parent.find('%s:%s' % (ns, name), namespaces=NSMAP)
        if node is not None:
            return node
