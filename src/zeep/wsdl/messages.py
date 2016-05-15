from collections import namedtuple

import six
from defusedxml.lxml import fromstring
from lxml import etree
from lxml.builder import ElementMaker

from zeep import xsd
from zeep.utils import qname_attr
from zeep.wsdl.utils import _soap_element
from zeep.xsd import Element

SerializedMessage = namedtuple('SerializedMessage', ['path', 'headers', 'content'])


class ConcreteMessage(object):
    def __init__(self, wsdl, name, operation):
        assert wsdl
        assert operation

        self.wsdl = wsdl
        self.namespace = {}
        self.operation = operation
        self.name = name

    def serialize(self, *args, **kwargs):
        raise NotImplementedError()

    def deserialize(self, node):
        raise NotImplementedError()

    def signature(self, as_output=False):
        if as_output:
            return self.body.type.name
        return self.body.type.signature()

    @classmethod
    def parse(cls, wsdl, xmlelement, abstract_message, operation):
        raise NotImplementedError()


class SoapMessage(ConcreteMessage):

    def __init__(self, wsdl, name, operation, nsmap):
        super(SoapMessage, self).__init__(wsdl, name, operation)
        self.nsmap = nsmap
        self.abstract = None  # Set during resolve()
        self.body = None
        self.header = None
        self.headerfault = None

    @classmethod
    def parse(cls, definitions, xmlelement, name, operation, nsmap):
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


class DocumentMessage(SoapMessage):
    """In the document message there are no additional wrappers, and the
    message parts appear directly under the SOAP Body element.

    """
    def serialize(self, *args, **kwargs):
        nsmap = self.nsmap.copy()
        nsmap.update(self.wsdl.schema._prefix_map)

        soap = ElementMaker(namespace=self.nsmap['soap-env'], nsmap=nsmap)
        body = header = None
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

        envelope = soap.Envelope()
        if header is not None:
            envelope.append(header)
        if body is not None:
            envelope.append(body)

        headers = {
            'SOAPAction': self.operation.soapaction,
        }
        return SerializedMessage(
            path=None, headers=headers, content=envelope)

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

            if isinstance(self.body.type, xsd.ComplexType):
                if len(self.body.type.properties()) == 1:
                    return self.body.type.properties()[0].type.name

            return self.body.type.name
        return self.body.type.signature()


class RpcMessage(SoapMessage):
    """In RPC messages each part is a parameter or a return value and appears
    inside a wrapper element within the body.

    The wrapper element is named identically to the operation name and its
    namespace is the value of the namespace attribute.  Each message part
    (parameter) appears under the wrapper, represented by an accessor named
    identically to the corresponding parameter of the call.  Parts are arranged
    in the same order as the parameters of the call.

    """

    def serialize(self, *args, **kwargs):
        nsmap = self.nsmap.copy()
        nsmap.update(self.wsdl.schema._prefix_map)

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

        envelope = soap.Envelope()
        envelope.append(body)

        headers = {
            'SOAPAction': self.operation.soapaction,
        }
        return SerializedMessage(
            path=None, headers=headers, content=envelope)

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

    def signature(self, as_output=False):
        result = xsd.ComplexType(children=[
            xsd.Element(etree.QName(etree.QName(name).localname), message.type)
            for name, message in self.abstract.parts.items()
        ])
        return result.signature()


class HttpMessage(ConcreteMessage):
    """Base class for HTTP Binding messages"""
    pass


class UrlEncoded(HttpMessage):
    """The urlEncoded element indicates that all the message parts are encoded
    into the HTTP request URI using the standard URI-encoding rules
    (name1=value&name2=value...).

    The names of the parameters correspond to the names of the message parts.
    Each value contributed by the part is encoded using a name=value pair. This
    may be used with GET to specify URL encoding, or with POST to specify a
    FORM-POST. For GET, the "?" character is automatically appended as
    necessary.

    """

    def serialize(self, *args, **kwargs):
        params = {key: None for key in self.abstract.parts.keys()}
        params.update(zip(self.abstract.parts.keys(), args))
        params.update(kwargs)
        headers = {'Content-Type': 'text/xml; charset=utf-8'}
        return SerializedMessage(
            path=self.operation.location, headers=headers, content=params)

    def signature(self, as_output=False):
        result = xsd.ComplexType(children=[
            xsd.Element(etree.QName(etree.QName(name).localname), message.type)
            for name, message in self.abstract.parts.items()
        ])
        return result.signature()

    def resolve(self, definitions, abstract_message):
        self.abstract = abstract_message
        self.params = xsd.Element(
             None,
             xsd.ComplexType(children=abstract_message.parts.values()))

    @classmethod
    def parse(cls, definitions, xmlelement, name, operation):
        obj = cls(definitions.wsdl, name, operation)
        return obj


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

    def serialize(self, *args, **kwargs):
        params = {key: None for key in self.abstract.parts.keys()}
        params.update(zip(self.abstract.parts.keys(), args))
        params.update(kwargs)
        headers = {'Content-Type': 'text/xml; charset=utf-8'}

        path = self.operation.location
        for key, value in params.items():
            path = path.replace('(%s)' % key, value if value is not None else '')
        return SerializedMessage(path=path, headers=headers, content='')

    def signature(self):
        result = xsd.ComplexType(children=[
            xsd.Element(etree.QName(etree.QName(name).localname), message.type)
            for name, message in self.abstract.parts.items()
        ])
        return result.signature()

    def resolve(self, definitions, abstract_message):
        self.abstract = abstract_message

    @classmethod
    def parse(cls, definitions, xmlelement, name, operation):
        obj = cls(definitions.wsdl, name, operation)
        return obj


class MimeMessage(ConcreteMessage):
    _nsmap = {
        'mime': 'http://schemas.xmlsoap.org/wsdl/mime/',
    }


class MimeContent(MimeMessage):
    """WSDL includes a way to bind abstract types to concrete messages in some
    MIME format.

    Bindings for the following MIME types are defined:

    - multipart/related
    - text/xml
    - application/x-www-form-urlencoded
    - Others (by specifying the MIME type string)

    The set of defined MIME types is both large and evolving, so it is not a
    goal for WSDL to exhaustively define XML grammar for each MIME type.

    """
    def __init__(self, wsdl, name, operation, content_type):
        super(MimeContent, self).__init__(wsdl, name, operation)
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

        return SerializedMessage(
            path=self.operation.location, headers=headers, content=data)

    def deserialize(self, node):
        node = fromstring(node)
        part = list(self.abstract.parts.values())[0]
        return part.type.parse_xmlelement(node)

    def signature(self, as_output=False):
        result = xsd.ComplexType(children=[
            xsd.Element(etree.QName(etree.QName(name).localname), message.type)
            for name, message in self.abstract.parts.items()
        ])
        return result.signature()

    def resolve(self, definitions, abstract_message):
        if abstract_message.parts:
            if not self.name:
                if len(abstract_message.parts.keys()) > 1:
                    part = abstract_message.parts
                else:
                    part = list(abstract_message.parts.values())[0]
            else:
                part = abstract_message.parts[self.name]
        else:
            part = None
        self.abstract = abstract_message
        self.body = part

    @classmethod
    def parse(cls, definitions, xmlelement, name, operation):
        content_type = None
        content_node = xmlelement.find('mime:content', namespaces=cls._nsmap)
        if content_node is not None:
            content_type = content_node.get('type')

        obj = cls(definitions.wsdl, name, operation, content_type)
        return obj


class MimeXML(MimeMessage):
    """To specify XML payloads that are not SOAP compliant (do not have a SOAP
    Envelope), but do have a particular schema, the mime:mimeXml element may be
    used to specify that concrete schema.

    The part attribute refers to a message part defining the concrete schema of
    the root XML element. The part attribute MAY be omitted if the message has
    only a single part. The part references a concrete schema using the element
    attribute for simple parts or type attribute for composite parts

    """
    def serialize(self, *args, **kwargs):
        raise NotImplementedError()

    def deserialize(self, node):
        node = fromstring(node)
        part = self.abstract.parts.values()[0]
        return part.element.parse(node)

    def resolve(self, definitions, abstract_message):
        self.abstract = abstract_message

    def signature(self, as_output=False):
        part = self.abstract.parts.values()[0]
        return part.element.type

    @classmethod
    def parse(cls, definitions, xmlelement, name, operation):
        obj = cls(definitions.wsdl, name, operation)
        return obj


class MimeMultipart(MimeMessage):
    """The multipart/related MIME type aggregates an arbitrary set of MIME
    formatted parts into one message using the MIME type "multipart/related".

    The mime:multipartRelated element describes the concrete format of such a
    message::

        <mime:multipartRelated>
            <mime:part> *
                <-- mime element -->
            </mime:part>
        </mime:multipartRelated>

    The mime:part element describes each part of a multipart/related message.
    MIME elements appear within mime:part to specify the concrete MIME type for
    the part. If more than one MIME element appears inside a mime:part, they
    are alternatives.

    """
    pass
