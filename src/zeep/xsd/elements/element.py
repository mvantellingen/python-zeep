import copy
import logging

from lxml import etree

from zeep import exceptions
from zeep.exceptions import UnexpectedElementError
from zeep.utils import qname_attr
from zeep.xsd.const import Nil, NotSet, xsi_ns
from zeep.xsd.context import XmlParserContext
from zeep.xsd.elements.base import Base
from zeep.xsd.utils import create_prefixed_name, max_occurs_iter

logger = logging.getLogger(__name__)

__all__ = ['Element']


class Element(Base):
    def __init__(self, name, type_=None, min_occurs=1, max_occurs=1,
                 nillable=False, default=None, is_substitution_group=False,
                 is_global=False, attr_name=None):

        if name is None:
            raise ValueError("name cannot be None", self.__class__)
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        self.name = name.localname if name else None
        self.qname = name
        self.type = type_
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.nillable = nillable
        self.is_global = is_global
        self.is_substitution_group = is_substitution_group
        self.known_substitution_elms = {}
        self.default = default
        self.attr_name = attr_name or self.name
        # assert type_

    def __str__(self):
        if self.type:
            if self.type.is_global:
                return '%s(%s)' % (self.name, self.type.qname)
            else:
                return '%s(%s)' % (self.name, self.type.signature())
        return '%s()' % self.name

    def __call__(self, *args, **kwargs):
        instance = self.type(*args, **kwargs)
        if hasattr(instance, '_xsd_type'):
            instance._xsd_elm = self
        return instance

    def __repr__(self):
        return '<%s(name=%r, type=%r)>' % (
            self.__class__.__name__, self.name, self.type)

    def __eq__(self, other):
        return (
            other is not None and
            self.__class__ == other.__class__ and
            self.__dict__ == other.__dict__)

    def get_prefixed_name(self, schema):
        return create_prefixed_name(self.qname, schema)

    @property
    def default_value(self):
        if self.accepts_multiple:
            return []
        if self.is_optional:
            return None
        return self.default

    def clone(self, name=None, min_occurs=1, max_occurs=1):
        new = copy.copy(self)

        if name:
            if not isinstance(name, etree.QName):
                name = etree.QName(name)
            new.name = name.localname
            new.qname = name
            new.attr_name = new.name

        new.min_occurs = min_occurs
        new.max_occurs = max_occurs
        return new

    def parse(self, xmlelement, schema, allow_none=False, context=None):
        """Process the given xmlelement. If it has an xsi:type attribute then
        use that for further processing. This should only be done for subtypes
        of the defined type but for now we just accept everything.

        This is the entrypoint for parsing an xml document.

        :param xmlelement: The XML element to parse
        :type xmlelements: lxml.etree._Element
        :param schema: The parent XML schema
        :type schema: zeep.xsd.Schema
        :param allow_none: Allow none
        :type allow_none: bool
        :param context: Optional parsing context (for inline schemas)
        :type context: zeep.xsd.context.XmlParserContext
        :return: dict or None

        """
        context = context or XmlParserContext()
        instance_type = qname_attr(xmlelement, xsi_ns('type'))
        xsd_type = None
        if instance_type:
            xsd_type = schema.get_type(instance_type, fail_silently=True)
        xsd_type = xsd_type or self.type
        return xsd_type.parse_xmlelement(
            xmlelement, schema, allow_none=allow_none, context=context,
            schema_type=self.type)

    def parse_kwargs(self, kwargs, name, available_kwargs):
        result = self.type.parse_kwargs(
            kwargs, name or self.attr_name, available_kwargs)
        if (len(result) < 1 and self.is_global and self.is_substitution_group
            and len(self.known_substitution_elms) > 0):
            for (elm_qname, elm) in self.known_substitution_elms.items():
                result = elm.type.parse_kwargs(kwargs, elm.name, available_kwargs)
                if len(result) > 0:
                    if name not in result:
                        result[name] = result[elm.name]
                    break
        return result

    def parse_xmlelement_substituted(self, xmlelements, schema, element_tag,
                                     substitution_group=None, context=None):
        if substitution_group is None:  # We didn't get one passed in.
            # Try to retrieve it from the schema.
            substitution_group = schema.get_substitution_group(self.qname)
        if not substitution_group:  # Still no substitution_group for this element.
            return None, None
        for sub_element_qname in substitution_group:
            if (element_tag.namespace and sub_element_qname.namespace and
               element_tag.namespace != sub_element_qname.namespace):
                continue
            if element_tag.localname == sub_element_qname.localname:
                # Try to find the substitute element in our schema
                substitute_element = schema.get_element(sub_element_qname)
                self.known_substitution_elms[sub_element_qname] = substitute_element
                xmlelement = xmlelements.popleft()
                item = substitute_element.parse(
                    xmlelement, schema, allow_none=True, context=context)
                return item, substitute_element.name
        return None, None

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        """Consume matching xmlelements and call parse() on each of them

        :param xmlelements: Dequeue of XML element objects
        :type xmlelements: collections.deque of lxml.etree._Element
        :param schema: The parent XML schema
        :type schema: zeep.xsd.Schema
        :param name: The name of the parent element
        :type name: str
        :param context: Optional parsing context (for inline schemas)
        :type context: zeep.xsd.context.XmlParserContext
        :return: dict or None

        """
        result = []
        num_matches = 0
        substitute_elm_name = None
        for _unused in max_occurs_iter(self.max_occurs):
            if not xmlelements:
                break

            # Workaround for SOAP servers which incorrectly use unqualified
            # or qualified elements in the responses (#170, #176). To make the
            # best of it we compare the full uri's if both elements have a
            # namespace. If only one has a namespace then only compare the
            # localname.

            element_tag = etree.QName(xmlelements[0].tag)
            # If both elements have a namespace and they don't match then skip
            differs_namespace = (element_tag.namespace and self.qname.namespace and
                                 element_tag.namespace != self.qname.namespace)
            if differs_namespace and schema.strict:
                # namespaces are different and we are on strict mode.
                # Bail out early, but check for a possible substitution group first.
                if not self.is_substitution_group:
                    break  # Can't check for substitutions

                substitution_group = schema.get_substitution_group(self.qname)
                assert substitution_group is not None, "Element is defined as a substitution group, but cannot load " \
                                                       "its substitution group from the schema."
                # Try early substitution.
                s_result, elm_name = self.parse_xmlelement_substituted(
                    xmlelements, schema, element_tag, substitution_group,
                    context=context)
                if s_result:
                    num_matches += 1
                    result.append(s_result)
                    substitute_elm_name = elm_name
                    continue
                else:
                    break
            # Compare just the localname in that case that:
            # a) The elements are in the same namespace _or_
            # b) Schema is configured in non-strict mode
            if (not differs_namespace or not schema.strict) and \
                (element_tag.localname == self.qname.localname):
                xmlelement = xmlelements.popleft()
                num_matches += 1
                item = self.parse(
                    xmlelement, schema, allow_none=True, context=context)
                result.append(item)
            else:
                # If the element passed doesn't match and the current one
                # Try late substitution
                substitution_group = schema.get_substitution_group(self.qname) \
                                     if schema else None

                if substitution_group:
                    s_result, elm_name = self.parse_xmlelement_substituted(
                        xmlelements, schema, element_tag, substitution_group,
                        context=context)
                    if s_result:
                        num_matches += 1
                        result.append(s_result)
                        substitute_elm_name = elm_name
                        continue
                # If the Element is not optional then throw an error
                if num_matches == 0 and not self.is_optional:
                    raise UnexpectedElementError(
                        "Unexpected element %r, expected %r" % (
                            element_tag.text, self.qname.text))
                break

        if not self.accepts_multiple:
            result = result[0] if result else None
            if substitute_elm_name:
                result = (result, substitute_elm_name)
        return result

    def render(self, parent, value, render_path=None):
        """Render the value(s) on the parent lxml.Element.

        This actually just calls _render_value_item for each value.

        """
        if not render_path:
            render_path = [self.qname.localname]

        assert parent is not None
        self.validate(value, render_path)

        if self.accepts_multiple and isinstance(value, list):
            for val in value:
                self._render_value_item(parent, val, render_path)
        else:
            self._render_value_item(parent, value, render_path)

    def _render_value_item(self, parent, value, render_path):
        """Render the value on the parent lxml.Element"""

        if value is Nil:
            elm = etree.SubElement(parent, self.qname)
            elm.set(xsi_ns('nil'), 'true')
            return

        if value is None or value is NotSet:
            if self.is_optional:
                return

            elm = etree.SubElement(parent, self.qname)
            if self.nillable:
                elm.set(xsi_ns('nil'), 'true')
            return

        node = etree.SubElement(parent, self.qname)
        xsd_type = getattr(value, '_xsd_type', self.type)

        if xsd_type != self.type:
            return value._xsd_type.render(node, value, xsd_type, render_path)
        return self.type.render(node, value, None, render_path)

    def validate(self, value, render_path=None):
        """Validate that the value is valid"""
        if self.accepts_multiple and isinstance(value, list):

            # Validate bounds
            if len(value) < self.min_occurs:
                raise exceptions.ValidationError(
                    "Expected at least %d items (minOccurs check)" % self.min_occurs,
                    path=render_path)
            elif self.max_occurs != 'unbounded' and len(value) > self.max_occurs:
                raise exceptions.ValidationError(
                    "Expected at most %d items (maxOccurs check)" % self.max_occurs,
                    path=render_path)

            for val in value:
                self._validate_item(val, render_path)
        else:
            if not self.is_optional and not self.nillable and value in (None, NotSet):
                raise exceptions.ValidationError(
                    "Missing element %s" % (self.name), path=render_path)

            self._validate_item(value, render_path)

    def _validate_item(self, value, render_path):
        if self.nillable and value in (None, NotSet):
            return

        try:
            self.type.validate(value, required=True)
        except exceptions.ValidationError as exc:
            raise exceptions.ValidationError(
                "The element %s is not valid: %s" % (self.qname, exc.message),
                path=render_path)

    def resolve_type(self):
        self.type = self.type.resolve()

    def resolve(self):
        self.resolve_type()
        return self

    def signature(self, schema=None, standalone=True):
        from zeep.xsd import ComplexType
        if self.type.is_global or (not standalone and self.is_global):
            value = self.type.get_prefixed_name(schema)
        else:
            value = self.type.signature(schema, standalone=False)

            if not standalone and isinstance(self.type, ComplexType):
                value = '{%s}' % value

        if standalone:
            value = '%s(%s)' % (self.get_prefixed_name(schema), value)

        if self.accepts_multiple:
            return '%s[]' % value
        return value
