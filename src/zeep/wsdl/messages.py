import copy
from collections import OrderedDict, namedtuple

import six
from defusedxml.lxml import fromstring
from lxml import etree
from lxml.builder import ElementMaker

from zeep import exceptions, xsd
from zeep.helpers import serialize_object
from zeep.utils import as_qname
from zeep.wsdl.utils import etree_to_string

SerializedMessage = namedtuple('SerializedMessage', ['path', 'headers', 'content'])


class ConcreteMessage(object):
    """Represents the wsdl:binding -> wsdl:operation -> input/ouput node"""
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
        if not self.body:
            return None

        if as_output:
            if isinstance(self.body.type, xsd.ComplexType):
                try:
                    if len(self.body.type.elements) == 1:
                        return self.body.type.elements[0][1].type.signature()
                except AttributeError:
                    return None

            return self.body.type.signature()

        parts = [self.body.type.signature()]
        if getattr(self, 'header', None):
            parts.append('_soapheaders={%s}' % self.header.signature())
        return ', '.join(part for part in parts if part)

    @classmethod
    def parse(cls, wsdl, xmlelement, abstract_message, operation):
        raise NotImplementedError()


class SoapMessage(ConcreteMessage):
    """Base class for the SOAP Document and RPC messages"""

    def __init__(self, wsdl, name, operation, type, nsmap):
        super(SoapMessage, self).__init__(wsdl, name, operation)
        self.nsmap = nsmap
        self.abstract = None  # Set during resolve()
        self.type = type

        self.body = xsd.Element(None, xsd.ComplexType([]))
        self.header = xsd.Element(None, xsd.ComplexType([]))
        self.envelope = None

    def serialize(self, *args, **kwargs):
        """Create a SerializedMessage for this message"""
        nsmap = self.nsmap.copy()
        nsmap.update(self.wsdl.types._prefix_map)

        soap = ElementMaker(namespace=self.nsmap['soap-env'], nsmap=nsmap)
        body = header = None

        # Create the soap:header element
        headers_value = kwargs.pop('_soapheaders', None)
        if headers_value:
            headers_value = copy.deepcopy(headers_value)
            header = soap.Header()
            if isinstance(headers_value, list):
                for header_value in headers_value:
                    if hasattr(header_value, '_xsd_elm'):
                        header_value._xsd_elm.render(header, header_value)
                    elif isinstance(header_value, etree._Element):
                        header.append(header_value)
                    else:
                        raise ValueError("Invalid value given to _soapheaders")
            elif isinstance(headers_value, dict):
                if not self.header:
                    raise ValueError(
                        "_soapheaders only accepts a dictionary if the wsdl "
                        "defines the headers.")
                headers_value = self.header(**headers_value)
                self.header.render(header, headers_value)
            else:
                raise ValueError("Invalid value given to _soapheaders")

        # Create the soap:body element
        if self.body:
            body_value = self.body(*args, **kwargs)
            body = soap.Body()
            self.body.render(body, body_value)

        # Create the soap:envelope
        envelope = soap.Envelope()
        if header is not None:
            envelope.append(header)
        if body is not None:
            envelope.append(body)

        headers = {
            'SOAPAction': '"%s"' % self.operation.soapaction
        }

        etree.cleanup_namespaces(envelope)
        return SerializedMessage(
            path=None, headers=headers, content=envelope)

    def deserialize(self, envelope):
        """Deserialize the SOAP:Envelope and return a CompoundValue with the
        result.

        """
        body = envelope.find('soap-env:Body', namespaces=self.nsmap)
        body_result = self._deserialize_body(body)

        header = envelope.find('soap-env:Header', namespaces=self.nsmap)
        headers_result = self._deserialize_headers(header)

        kwargs = body_result
        kwargs.update(headers_result)
        result = self.envelope(**kwargs)

        # If the message
        if self.header.type._element:
            return result

        result = result.body
        if len(result) > 1:
            return result
        elif len(result) == 0:
            return None

        result = next(iter(result.__values__.values()))
        if isinstance(result, xsd.CompoundValue):
            children = result._xsd_type.elements
            if len(children) == 1:
                item_name, item_element = children[0]
                retval = getattr(result, item_name)
                return retval
        return result

    def signature(self, as_output=False):
        if not self.envelope:
            return None

        if as_output:
            if isinstance(self.envelope.type, xsd.ComplexType):
                try:
                    if len(self.envelope.type.elements) == 1:
                        return self.envelope.type.elements[0][1].type.signature()
                except AttributeError:
                    return None
            return self.envelope.type.signature()

        parts = [self.body.type.signature()]
        if self.header.type._element:
            parts.append('_soapheaders={%s}' % self.header.signature())
        return ', '.join(part for part in parts if part)

    @classmethod
    def parse(cls, definitions, xmlelement, operation, type, nsmap):
        """Parse a wsdl:binding/wsdl:operation/wsdl:operation for the SOAP
        implementation.

        Each wsdl:operation can contain three child nodes:
         - input
         - output
         - fault

        Definition for input/output::

          <input>
            <soap:body parts="nmtokens"? use="literal|encoded"
                       encodingStyle="uri-list"? namespace="uri"?>

            <soap:header message="qname" part="nmtoken" use="literal|encoded"
                         encodingStyle="uri-list"? namespace="uri"?>*
              <soap:headerfault message="qname" part="nmtoken"
                                use="literal|encoded"
                                encodingStyle="uri-list"? namespace="uri"?/>*
            </soap:header>
          </input>

        And the definition for fault::

           <soap:fault name="nmtoken" use="literal|encoded"
                       encodingStyle="uri-list"? namespace="uri"?>

        """
        name = xmlelement.get('name')
        obj = cls(definitions.wsdl, name, operation, nsmap=nsmap, type=type)
        tns = definitions.target_namespace

        info = {
            'body': {},
            'header': [],
        }

        # parse soap:body
        # <soap:body parts="nmtokens"? use="literal|encoded"?
        #   encodingStyle="uri-list"? namespace="uri"?>
        body = xmlelement.find('soap:body', namespaces=operation.binding.nsmap)
        if body is not None:
            info['body'] = {
                'part': body.get('part'),
                'use': body.get('use', 'literal'),
                'encodingStyle': body.get('encodingStyle'),
                'namespace': body.get('namespace'),
            }

        # Parse soap:header (multiple)
        elements = xmlelement.findall(
            'soap:header', namespaces=operation.binding.nsmap)
        info['header'] = cls._parse_header(elements, tns, operation)

        obj._info = info
        return obj

    @classmethod
    def _parse_header(cls, xmlelements, tns, operation):
        """Parse the soap:header and optionally included soap:headerfault elements

          <soap:header
            message="qname"
            part="nmtoken"
            use="literal|encoded"
            encodingStyle="uri-list"?
            namespace="uri"?
          />*

        The header can optionally contain one ore more soap:headerfault
        elements which can contain the same attributes as the soap:header::

           <soap:headerfault message="qname" part="nmtoken" use="literal|encoded"
                             encodingStyle="uri-list"? namespace="uri"?/>*

        """
        result = []
        for xmlelement in xmlelements:
            data = cls._parse_header_element(xmlelement, tns)

            # Add optional soap:headerfault elements
            data['faults'] = []
            fault_elements = xmlelement.findall(
                'soap:headerfault', namespaces=operation.binding.nsmap)
            for fault_element in fault_elements:
                fault_data = cls._parse_header_element(fault_element, tns)
                data['faults'].append(fault_data)

            result.append(data)
        return result

    @classmethod
    def _parse_header_element(cls, xmlelement, tns):
        attributes = xmlelement.attrib
        message_qname = as_qname(
            attributes['message'], xmlelement.nsmap, tns)

        try:
            return {
                'message': message_qname,
                'part': attributes['part'],
                'use': attributes['use'],
                'encodingStyle': attributes.get('encodingStyle'),
                'namespace': attributes.get('namespace'),
            }
        except KeyError:
            raise exceptions.WsdlSyntaxError("Invalid soap:header(fault)")

    def _create_envelope_element(self):
        """Create combined `envelope` complexType which contains both the
        elements from the body and the headers.
        """
        all_elements = []
        if self.body.signature():
            all_elements.append(xsd.Element('body', self.body.type))
        else:
            all_elements.append(xsd.Element('body', xsd.ComplexType([])))
        if self.header.signature():
            all_elements.append(xsd.Element('header', self.header.type))
        else:
            all_elements.append(xsd.Element('header', xsd.ComplexType([])))

        retval = xsd.Element(None, xsd.ComplexType(all_elements))
        return retval

    def _deserialize_headers(self, xmlelement):
        """Deserialize the values in the SOAP:Header element"""
        if not self.header or xmlelement is None:
            return {}

        result = self.header.parse(xmlelement, self.wsdl.types)
        if result is not None:
            return {'header': result}
        return {}

    def _resolve_header(self, info, definitions, parts):
        sequence = xsd.Sequence()
        if not info:
            return xsd.Element(None, xsd.ComplexType(sequence))

        for item in info:
            message_name = item['message'].text
            part_name = item['part']

            message = definitions.get('messages', message_name)
            if message == self.abstract:
                del parts[part_name]
            element = message.parts[part_name].element.clone()
            element.attr_name = part_name
            sequence.append(element)
        return xsd.Element(None, xsd.ComplexType(sequence))


class DocumentMessage(SoapMessage):
    """In the document message there are no additional wrappers, and the
    message parts appear directly under the SOAP Body element.

    """

    def __init__(self, *args, **kwargs):
        super(DocumentMessage, self).__init__(*args, **kwargs)
        self._is_body_wrapped = False

    def resolve(self, definitions, abstract_message):
        """Resolve the data in the self._info dict (set via parse())

        This creates three xsd.Element objects:

            - self.header
            - self.body
            - self.envelope (combination of headers and body)

        XXX headerfaults are not implemented yet.

        """
        # If this message has no parts then we have nothing to do. This might
        # happen for output messages which don't return anything.
        if not abstract_message.parts:
            return

        self.abstract = abstract_message
        parts = OrderedDict(self.abstract.parts)

        # Process the headers
        self.header = self._resolve_header(
            self._info['header'], definitions, parts)

        # Process the body
        body_info = self._info['body']
        if body_info:
            # If the part name is omitted then all parts are available under
            # the soap:body tag. Otherwise only the part with the given name.
            if body_info['part']:
                part_name = body_info['part']
                sub_elements = [parts[part_name].element]
            else:
                sub_elements = []
                for part_name, part in parts.items():
                    element = part.element.clone()
                    element.attr_name = part_name or element.name
                    sub_elements.append(element)

            if len(sub_elements) > 1:
                self.body = xsd.Element(
                    None, xsd.ComplexType(xsd.All(sub_elements)))
                self._is_body_wrapped = True
            else:
                self.body = sub_elements[0]
                self._is_body_wrapped = False

        # self.envelope = self.body
        self.envelope = self._create_envelope_element()

    def _deserialize_body(self, xmlelement):
        if self._is_body_wrapped:
            result = self.body.parse(xmlelement, self.wsdl.types)
        else:
            # For now we assume that the body only has one child since only
            # one part is specified in the wsdl. This should be handled way
            # better
            # XXX
            xmlelement = xmlelement.getchildren()[0]
            result = self.body.parse(xmlelement, self.wsdl.types)
        return {'body': result}


class RpcMessage(SoapMessage):
    """In RPC messages each part is a parameter or a return value and appears
    inside a wrapper element within the body.

    The wrapper element is named identically to the operation name and its
    namespace is the value of the namespace attribute.  Each message part
    (parameter) appears under the wrapper, represented by an accessor named
    identically to the corresponding parameter of the call.  Parts are arranged
    in the same order as the parameters of the call.

    """

    def resolve(self, definitions, abstract_message):
        """Override the default `SoapMessage.resolve()` since we need to wrap
        the parts in an element.

        """
        # If this message has no parts then we have nothing to do. This might
        # happen for output messages which don't return anything.
        if not abstract_message.parts and self.type != 'input':
            return

        self.abstract = abstract_message
        parts = OrderedDict(self.abstract.parts)

        self.header = self._resolve_header(
            self._info['header'], definitions, parts)

        # Each part is a parameter or a return value and appears inside a
        # wrapper element within the body named identically to the operation
        # name and its namespace is the value of the namespace attribute.
        body_info = self._info['body']
        if body_info:
            namespace = self._info['body']['namespace']
            if self.type == 'input':
                tag_name = etree.QName(namespace, self.operation.name)
            else:
                tag_name = etree.QName(namespace, self.abstract.name.localname)

            # Create the xsd element to create/parse the response. Each part
            # is a sub element of the root node (which uses the operation name)
            elements = []
            for name, msg in parts.items():
                if msg.element:
                    elements.append(msg.element)
                else:
                    elements.append(xsd.Element(name, msg.type))

            self.body = xsd.Element(
                tag_name, xsd.ComplexType(xsd.Sequence(elements)))

        self.envelope = self._create_envelope_element()

    def _deserialize_body(self, body_element):
        """The name of the wrapper element is not defined. The WS-I defines
        that it should be the operation name with the 'Response' string as
        suffix. But lets just do it really stupid for now and use the first
        element.

        """
        response_element = body_element.getchildren()[0]
        result = self.body.parse(response_element, self.wsdl.types)
        return {'body': result}


class HttpMessage(ConcreteMessage):
    """Base class for HTTP Binding messages"""

    def resolve(self, definitions, abstract_message):
        self.abstract = abstract_message

        children = []
        for name, message in self.abstract.parts.items():
            if message.element:
                elm = message.element.clone(name)
            else:
                elm = xsd.Element(name, message.type)
            children.append(elm)
        self.body = xsd.Element(
            self.operation.name, xsd.ComplexType(xsd.Sequence(children)))


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

    @classmethod
    def parse(cls, definitions, xmlelement, operation):
        name = xmlelement.get('name')
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

    @classmethod
    def parse(cls, definitions, xmlelement, operation):
        name = xmlelement.get('name')
        obj = cls(definitions.wsdl, name, operation)
        return obj


class MimeMessage(ConcreteMessage):
    _nsmap = {
        'mime': 'http://schemas.xmlsoap.org/wsdl/mime/',
    }

    def __init__(self, wsdl, name, operation, part_name):
        super(MimeMessage, self).__init__(wsdl, name, operation)
        self.part_name = part_name

    def resolve(self, definitions, abstract_message):
        """Resolve the body element

        The specs are (again) not really clear how to handle the message
        parts in relation the message element vs type. The following strategy
        is chosen, which seem to work:

         - If the message part has a name and it maches then set it as body
         - If the message part has a name but it doesn't match but there are no
           other message parts, then just use that one.
         - If the message part has no name then handle it like an rpc call,
           in other words, each part is an argument.

        """
        self.abstract = abstract_message
        if self.part_name and self.abstract.parts:
            if self.part_name in self.abstract.parts:
                message = self.abstract.parts[self.part_name]
            elif len(self.abstract.parts) == 1:
                message = list(self.abstract.parts.values())[0]
            else:
                raise ValueError(
                    "Multiple parts for message %r while no matching part found" % self.part_name)

            if message.element:
                self.body = message.element
            else:
                elm = xsd.Element(self.part_name, message.type)
                self.body = xsd.Element(
                    self.operation.name, xsd.ComplexType(xsd.Sequence([elm])))
        else:
            children = []
            for name, message in self.abstract.parts.items():
                if message.element:
                    elm = message.element.clone(name)
                else:
                    elm = xsd.Element(name, message.type)
                children.append(elm)
            self.body = xsd.Element(
                self.operation.name, xsd.ComplexType(xsd.Sequence(children)))


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
    def __init__(self, wsdl, name, operation, content_type, part_name):
        super(MimeContent, self).__init__(wsdl, name, operation, part_name)
        self.content_type = content_type

    def serialize(self, *args, **kwargs):
        value = self.body(*args, **kwargs)
        headers = {
            'Content-Type': self.content_type
        }

        data = ''
        if self.content_type == 'application/x-www-form-urlencoded':
            items = serialize_object(value)
            data = six.moves.urllib.parse.urlencode(items)
        elif self.content_type == 'text/xml':
            document = etree.Element('root')
            self.body.render(document, value)
            data = etree_to_string(document.getchildren()[0])

        return SerializedMessage(
            path=self.operation.location, headers=headers, content=data)

    def deserialize(self, node):
        node = fromstring(node)
        part = list(self.abstract.parts.values())[0]
        return part.type.parse_xmlelement(node)

    @classmethod
    def parse(cls, definitions, xmlelement, operation):
        name = xmlelement.get('name')

        part_name = content_type = None
        content_node = xmlelement.find('mime:content', namespaces=cls._nsmap)
        if content_node is not None:
            content_type = content_node.get('type')
            part_name = content_node.get('part')

        obj = cls(definitions.wsdl, name, operation, content_type, part_name)
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
        part = next(iter(self.abstract.parts.values()), None)
        return part.element.parse(node, self.wsdl.types)

    @classmethod
    def parse(cls, definitions, xmlelement, operation):
        name = xmlelement.get('name')
        part_name = None

        content_node = xmlelement.find('mime:mimeXml', namespaces=cls._nsmap)
        if content_node is not None:
            part_name = content_node.get('part')
        obj = cls(definitions.wsdl, name, operation, part_name)
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
