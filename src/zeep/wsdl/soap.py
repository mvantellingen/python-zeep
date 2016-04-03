import six
from lxml import etree
from lxml.builder import ElementMaker

from zeep.exceptions import Fault
from zeep.utils import get_qname, parse_qname, process_signature
from zeep.wsdl.definitions import Binding, ConcreteMessage, Operation


class SoapBinding(Binding):

    @classmethod
    def match(cls, node):
        soap_node = node.find('soap:binding', namespaces=cls.nsmap)
        return soap_node is not None

    def create_message(self, operation, *args, **kwargs):
        if isinstance(operation, six.string_types):
            operation = self.get(operation)
            if not operation:
                raise ValueError("Operation not found")

        nsmap = self.nsmap.copy()
        nsmap['ns0'] = self.wsdl.schema.target_namespace

        body, header, headerfault = operation.create(*args, **kwargs)
        soap = ElementMaker(namespace=self.nsmap['soap-env'], nsmap=nsmap)

        envelope = soap.Envelope()
        if header is not None:
            envelope.append(header)
        if body is not None:
            envelope.append(body)
        return envelope

    def send(self, transport, options, operation, args, kwargs):
        """Called from the service"""
        operation = self.get(operation)
        if not operation:
            raise ValueError("Operation not found")

        envelope = self.create_message(operation, *args, **kwargs)
        http_headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': operation.soapaction,
        }
        response = transport.post(
            options['address'], etree.tostring(envelope), http_headers)
        return self.process_reply(operation, response)

    def process_reply(self, operation, response):
        if response.status_code != 200:
            return self.process_error(response.content)
            raise NotImplementedError("No error handling yet!")

        envelope = etree.fromstring(response.content)
        return operation.process_reply(envelope)

    def process_error(self, response):
        doc = etree.fromstring(response)
        fault_node = doc.find(
            'soap-env:Body/soap-env:Fault', namespaces=self.nsmap)

        if fault_node is None:
            raise Fault('Unknown fault occured')

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
        address_node = xmlelement.find('soap:address', namespaces=self.nsmap)
        return {
            'address': address_node.get('location')
        }

    @classmethod
    def parse(cls, wsdl, xmlelement):
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
        name = get_qname(
            xmlelement, 'name', wsdl.target_namespace, as_text=False)
        port_name = get_qname(xmlelement, 'type', wsdl.target_namespace)
        port_type = wsdl.ports[port_name]

        obj = cls(name, port_type)

        # The soap:binding element contains the transport method and
        # default style attribute for the operations.
        soap_node = xmlelement.find('soap:binding', namespaces=cls.nsmap)
        transport = soap_node.get('transport')
        if transport != 'http://schemas.xmlsoap.org/soap/http':
            raise NotImplementedError("Only soap/http is supported for now")
        default_style = soap_node.get('style', 'document')

        obj.transport = transport
        obj.default_style = default_style

        for node in xmlelement.findall('wsdl:operation', namespaces=cls.nsmap):
            operation = SoapOperation.parse(wsdl, node, obj, nsmap=cls.nsmap)

            # XXX: operation name is not unique
            obj.operations[operation.name.text] = operation

        return obj


class Soap11Binding(SoapBinding):
    nsmap = {
        'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
        'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
        'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
    }


class Soap12Binding(SoapBinding):
    nsmap = {
        'soap': 'http://schemas.xmlsoap.org/wsdl/soap12/',
        'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
        'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
    }


class SoapOperation(Operation):

    def __init__(self, *args, **kwargs):
        self.nsmap = kwargs.pop('nsmap')
        super(SoapOperation, self).__init__(*args, **kwargs)

    def process_reply(self, envelope):
        node = envelope.find('soap-env:Body', namespaces=self.nsmap)
        return self.output.deserialize(node)

    @classmethod
    def parse(cls, wsdl, xmlelement, binding, nsmap):
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
        soap_node = xmlelement.find('soap:operation', namespaces=nsmap)
        action = None
        if soap_node is not None:
            action = soap_node.get('soapAction')
            style = soap_node.get('style', binding.default_style)
        else:
            style = binding.default_style

        obj = cls(name, abstract_operation, nsmap=nsmap)
        obj.soapaction = action
        obj.style = style

        if style == 'rpc':
            message_class = RpcMessage
        else:
            message_class = DocumentMessage

        for node in xmlelement.getchildren():
            tag_name = etree.QName(node.tag).localname
            if tag_name not in ('input', 'output', 'fault'):
                continue

            if tag_name == 'fault':
                fault_name = node.get('name')
                abstract = abstract_operation.get(tag_name, fault_name)
                msg = message_class.parse(wsdl, node, abstract, obj, nsmap)
                obj.faults[msg.name] = msg

            else:
                abstract = getattr(abstract_operation, tag_name)
                msg = message_class.parse(wsdl, node, abstract, obj, nsmap)
                setattr(obj, tag_name, msg)

        return obj


class SoapMessage(ConcreteMessage):

    def __init__(self, *args, **kwargs):
        self.nsmap = kwargs.pop('nsmap')
        super(SoapMessage, self).__init__(*args, **kwargs)

    @classmethod
    def parse(cls, wsdl, xmlelement, abstract_message, operation, nsmap):
        """
        Example::

              <output>
                <soap:body use="literal"/>
              </output>

        """
        obj = cls(wsdl, abstract_message, operation, nsmap=nsmap)

        body = xmlelement.find('soap:body', namespaces=nsmap)
        header = xmlelement.find('soap:header', namespaces=nsmap)
        headerfault = xmlelement.find('soap:headerfault', namespaces=nsmap)

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

        part_names = list(abstract_message.parts.keys())
        if header_info:
            part_name = header_info['part']

            if header_info['message']:
                msg = wsdl.messages[header_info['message']]
                obj.header = msg.parts[part_name]
                if msg == abstract_message:
                    part_names.remove(part_name)
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


class RpcMessage(SoapMessage):
    def serialize(self, *args, **kwargs):
        soap = ElementMaker(namespace=self.nsmap['soap-env'], nsmap=self.nsmap)
        tag_name = etree.QName(
            self.namespace['body'], self.abstract.name.localname)

        body = soap.Body()
        method = etree.SubElement(body, tag_name)

        param_order = self.signature()
        items = process_signature(param_order, args, kwargs)
        for key, value in items.items():
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
            else:
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

        # FIXME (not so sure about this): If the response object has only one
        # property then return that property
        item = result[0]
        if len(item.type.properties()) == 1:
            return getattr(item, item.type.properties()[0].name)
        return item
