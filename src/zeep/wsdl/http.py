import six
from lxml import etree
from defusedxml.lxml import fromstring

from zeep import xsd
from zeep.utils import qname_attr
from zeep.wsdl.definitions import Binding, ConcreteMessage, Operation

NSMAP = {
    'http': 'http://schemas.xmlsoap.org/wsdl/http/',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'mime': 'http://schemas.xmlsoap.org/wsdl/mime/',
}


class HttpBinding(Binding):

    def create_message(self, operation, *args, **kwargs):
        if isinstance(operation, six.string_types):
            operation = self.get(operation)
            if not operation:
                raise ValueError("Operation not found")
        return operation.create(*args, **kwargs)

    def process_service_port(self, xmlelement):
        address_node = xmlelement.find('http:address', namespaces=NSMAP)
        if address_node is None:
            raise ValueError("No `http:address` node found")

        return {
            'address': address_node.get('location')
        }

    @classmethod
    def parse(cls, definitions, xmlelement):
        name = qname_attr(xmlelement, 'name', definitions.target_namespace)
        port_name = qname_attr(xmlelement, 'type', definitions.target_namespace)

        obj = cls(definitions.wsdl, name, port_name)
        for node in xmlelement.findall('wsdl:operation', namespaces=NSMAP):
            operation = HttpOperation.parse(definitions, node, obj)
            obj._operation_add(operation)
        return obj

    def process_reply(self, operation, response):
        if response.status_code != 200:
            return self.process_error(response.content)
            raise NotImplementedError("No error handling yet!")
        return operation.process_reply(response.content)


class HttpPostBinding(HttpBinding):

    def send(self, client, options, operation, args, kwargs):
        """Called from the service"""
        operation = self.get(operation)
        if not operation:
            raise ValueError("Operation not found")

        path, headers, body = self.create_message(operation, *args, **kwargs)
        headers.setdefault('Content-Type', 'text/xml; charset=utf-8')
        url = options['address'] + path

        response = client.transport.post(url, body, headers)
        return self.process_reply(operation, response)

    @classmethod
    def match(cls, node):
        http_node = node.find(etree.QName(NSMAP['http'], 'binding'))
        return http_node is not None and http_node.get('verb') == 'POST'


class HttpGetBinding(HttpBinding):

    def send(self, client, options, operation, args, kwargs):
        """Called from the service"""
        operation = self.get(operation)
        if not operation:
            raise ValueError("Operation not found")

        path, headers, params = self.create_message(operation, *args, **kwargs)
        headers.setdefault('Content-Type', 'text/xml; charset=utf-8')
        url = options['address'] + path

        response = client.transport.get(url, params, headers)
        return self.process_reply(operation, response)

    @classmethod
    def match(cls, node):
        http_node = node.find(etree.QName(NSMAP['http'], 'binding'))
        return http_node is not None and http_node.get('verb') == 'GET'


class HttpOperation(Operation):
    def __init__(self, name, binding, location):
        super(HttpOperation, self).__init__(name, binding)
        self.location = location

    def process_reply(self, envelope):
        return self.output.deserialize(envelope)

    @classmethod
    def parse(cls, definitions, xmlelement, binding):
        """

            <wsdl:operation name="GetLastTradePrice">
              <http:operation location="GetLastTradePrice"/>
              <wsdl:input>
                <mime:content type="application/x-www-form-urlencoded"/>
              </wsdl:input>
              <wsdl:output>
                <mime:mimeXml/>
              </wsdl:output>
            </wsdl:operation>

        """
        name = xmlelement.get('name')

        http_operation = xmlelement.find('http:operation', namespaces=NSMAP)
        location = http_operation.get('location')
        obj = cls(name, binding, location)

        for node in xmlelement.getchildren():
            tag_name = etree.QName(node.tag).localname
            if tag_name not in ('input', 'output'):
                continue
            name = node.get('name')

            # XXX Multiple mime types may be declared as alternatives
            message_node = node.getchildren()[0]
            message_class = None
            if message_node.tag == etree.QName(NSMAP['http'], 'urlEncoded'):
                message_class = UrlEncoded
            elif message_node.tag == etree.QName(NSMAP['http'], 'urlReplacement'):
                message_class = UrlReplacement
            elif message_node.tag == etree.QName(NSMAP['mime'], 'content'):
                message_class = MimeContent
            elif message_node.tag == etree.QName(NSMAP['mime'], 'mimeXml'):
                message_class = MimeXML

            if message_class:
                msg = message_class.parse(
                    definitions, node, name, tag_name, obj)
                assert msg
                setattr(obj, tag_name, msg)
        return obj

    def resolve(self, definitions):
        super(HttpOperation, self).resolve(definitions)
        if self.output:
            self.output.resolve(definitions, self.abstract.output)
        if self.input:
            self.input.resolve(definitions, self.abstract.input)


class HttpMessage(ConcreteMessage):
    pass


class UrlEncoded(HttpMessage):

    def serialize(self, *args, **kwargs):
        params = {key: None for key in self.abstract.parts.keys()}
        params.update(zip(self.abstract.parts.keys(), args))
        params.update(kwargs)

        return self.operation.location, {}, params

    @classmethod
    def parse(cls, definitions, xmlelement, name, tag_name, operation):
        obj = cls(definitions.wsdl, name, operation)
        return obj

    def resolve(self, definitions, abstract_message):
        self.abstract = abstract_message
        self.params = xsd.Element(
             None,
             xsd.ComplexType(children=abstract_message.parts.values()))

    def signature(self, as_output=False):
        result = xsd.ComplexType(children=[
            xsd.Element(etree.QName(etree.QName(name).localname), message.type)
            for name, message in self.abstract.parts.items()
        ])
        return result.signature()


class UrlReplacement(HttpMessage):
    """The http:urlReplacement element indicates that all the message parts
    are encoded into the HTTP request URI using a replacement algorithm.

    - The relative URI value of http:operation is searched for a set of search
      patterns.
    - The search occurs before the value of the http:operation is combined with
      the value of the location attribute from http:address.
    - There is one search pattern for each message part. The search pattern
      string is the name of the message part surrounded with parenthesis "("
      and ")".
    - For each match, the value of the corresponding message part is
      substituted for the match at the location of the match.
    - Matches are performed before any values are replaced (replaced values do
      not trigger additional matches).

    Message parts MUST NOT have repeating values.
    <http:urlReplacement/>

    """

    @classmethod
    def parse(cls, definitions, xmlelement, name, tag_name, operation):
        obj = cls(definitions.wsdl, name, operation)
        return obj

    def resolve(self, definitions, abstract_message):
        self.abstract = abstract_message

    def serialize(self, *args, **kwargs):
        params = {key: None for key in self.abstract.parts.keys()}
        params.update(zip(self.abstract.parts.keys(), args))
        params.update(kwargs)

        url = self.operation.location
        for key, value in params.items():
            url = url.replace('(%s)' % key, value if value is not None else '')
        return url, {}, None

    def signature(self):
        result = xsd.ComplexType(children=[
            xsd.Element(etree.QName(etree.QName(name).localname), message.type)
            for name, message in self.abstract.parts.items()
        ])
        return result.signature()


class MimeContent(HttpMessage):

    def __init__(self, wsdl, name, operation, content_type):
        super(HttpMessage, self).__init__(wsdl, name, operation)
        self.content_type = content_type

    def serialize(self, *args, **kwargs):
        result = xsd.ComplexType(children=[
            xsd.Element(etree.QName(etree.QName(name).localname), message.type)
            for name, message in self.abstract.parts.items()
        ])
        value = result(*args, **kwargs)
        headers = {
            'Content-Type': self.content_type
        }

        data = ''
        if self.content_type == 'application/x-www-form-urlencoded':
            data = six.moves.urllib.parse.urlencode(result.serialize(value))

        return self.operation.location, headers, data

    def deserialize(self, node):
        pass

    @classmethod
    def parse(cls, definitions, xmlelement, name, tag_name, operation):
        content_type = None
        content_node = xmlelement.find('mime:content', namespaces=NSMAP)
        if content_node is not None:
            content_type = content_node.get('type')

        obj = cls(definitions.wsdl, name, operation, content_type)
        return obj

    def resolve(self, definitions, abstract_message):
        if abstract_message.parts:
            if not self.name:
                if len(abstract_message.parts.keys()) > 1:
                    part = abstract_message.parts
                else:
                    part = abstract_message.parts.values()[0]
            else:
                part = abstract_message.parts[self.name]
        else:
            part = None
        self.abstract = abstract_message
        self.body = part

    def signature(self, as_output=False):
        result = xsd.ComplexType(children=[
            xsd.Element(etree.QName(etree.QName(name).localname), message.type)
            for name, message in self.abstract.parts.items()
        ])
        return result.signature()


class MimeXML(HttpMessage):

    def deserialize(self, node):
        node = fromstring(node)
        part = self.abstract.parts.values()[0]
        return part.element.parse(node)

    @classmethod
    def parse(cls, definitions, xmlelement, name, tag_name, operation):
        obj = cls(definitions.wsdl, name, operation)
        return obj

    def resolve(self, definitions, abstract_message):
        self.abstract = abstract_message

    def signature(self, as_output=False):
        part = self.abstract.parts.values()[0]
        return part.element.type


class MimeMultipart(ConcreteMessage):
    pass
