import copy
import logging

from lxml import etree

from zeep import exceptions
from zeep.exceptions import UnexpectedElementError
from zeep.utils import qname_attr
from zeep.xsd.const import xsi_ns
from zeep.xsd.context import XmlParserContext
from zeep.xsd.utils import max_occurs_iter
from zeep.xsd.valueobjects import AnyObject  # cyclic import / FIXME

logger = logging.getLogger(__name__)


class Base(object):

    @property
    def accepts_multiple(self):
        return self.max_occurs != 1

    @property
    def default_value(self):
        return None

    @property
    def is_optional(self):
        return self.min_occurs == 0

    def parse_args(self, args, index=0):
        result = {}
        if not args:
            return result, args, index

        value = args[index]
        index += 1
        return {self.attr_name: value}, args, index

    def parse_kwargs(self, kwargs, name, available_kwargs):
        raise NotImplementedError()

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        """Consume matching xmlelements and call parse() on each of them"""
        raise NotImplementedError()

    def signature(self, depth=()):
        return ''


class Any(Base):
    name = None

    def __init__(self, max_occurs=1, min_occurs=1, process_contents='strict',
                 restrict=None):
        """

        :param process_contents: Specifies how the XML processor should handle
                                 validation against the elements specified by
                                 this any element
        :type process_contents: str (strict, lax, skip)

        """
        super(Any, self).__init__()
        self.max_occurs = max_occurs
        self.min_occurs = min_occurs
        self.restrict = restrict
        self.process_contents = process_contents

        # cyclic import
        from zeep.xsd.builtins import AnyType
        self.type = AnyType()

    def __call__(self, any_object):
        return any_object

    def __repr__(self):
        return '<%s(name=%r)>' % (self.__class__.__name__, self.name)

    def accept(self, value):
        return True

    def parse(self, xmlelement, schema, context=None):
        if self.process_contents == 'skip':
            return xmlelement

        qname = etree.QName(xmlelement.tag)
        for context_schema in context.schemas:
            if qname.namespace in context_schema._schemas:
                schema = context_schema
                break

        xsd_type = qname_attr(xmlelement, xsi_ns('type'))
        if xsd_type is not None:
            xsd_type = schema.get_type(xsd_type)
            return xsd_type.parse_xmlelement(xmlelement, schema, context=context)

        try:
            element = schema.get_element(xmlelement.tag)
            return element.parse(xmlelement, schema, context=context)
        except (exceptions.NamespaceError, exceptions.LookupError):
            return xmlelement

    def parse_kwargs(self, kwargs, name, available_kwargs):
        if name in available_kwargs:
            available_kwargs.remove(name)
            value = kwargs[name]
            return {name: value}
        return {}

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        """Consume matching xmlelements and call parse() on each of them"""
        result = []

        for i in max_occurs_iter(self.max_occurs):
            if xmlelements:
                xmlelement = xmlelements.popleft()
                item = self.parse(xmlelement, schema, context=context)
                if item is not None:
                    result.append(item)
            else:
                break

        if not self.accepts_multiple:
            result = result[0] if result else None
        return result

    def render(self, parent, value):
        assert parent is not None
        if self.accepts_multiple and isinstance(value, list):
            from zeep.xsd import SimpleType

            if isinstance(self.restrict, SimpleType):
                for val in value:
                    node = etree.SubElement(parent, 'item')
                    node.set(xsi_ns('type'), self.restrict.qname)
                    self._render_value_item(node, val)
            elif self.restrict:
                for val in value:
                    node = etree.SubElement(parent, self.restrict.name)
                    # node.set(xsi_ns('type'), self.restrict.qname)
                    self._render_value_item(node, val)
            else:
                for val in value:
                    self._render_value_item(parent, val)
        else:
            self._render_value_item(parent, value)

    def _render_value_item(self, parent, value):
        if value is None:  # can be an lxml element
            return

        # Check if we received a proper value object. If we receive the wrong
        # type then return a nice error message
        if self.restrict:
            expected_types = (etree._Element,) + self.restrict.accepted_types
        else:
            expected_types = (etree._Element, AnyObject)

        if not isinstance(value, expected_types):
            type_names = [
                '%s.%s' % (t.__module__, t.__name__) for t in expected_types
            ]
            err_message = "Any element received object of type %r, expected %s" % (
                type(value).__name__, ' or '.join(type_names))

            raise TypeError('\n'.join((
                err_message,
                "See http://docs.python-zeep.org/en/master/datastructures.html"
                "#any-objects for more information"
            )))

        if isinstance(value, etree._Element):
            parent.append(value)

        elif self.restrict:
            if isinstance(value, list):
                for val in value:
                    self.restrict.render(parent, val)
            else:
                self.restrict.render(parent, value)
        else:
            if isinstance(value.value, list):
                for val in value.value:
                    value.xsd_elm.render(parent, val)
            else:
                value.xsd_elm.render(parent, value.value)

    def resolve(self):
        return self

    def signature(self, depth=()):
        if self.restrict:
            base = self.restrict.name
        else:
            base = 'ANY'

        if self.accepts_multiple:
            return '%s[]' % base
        return base


class Element(Base):
    def __init__(self, name, type_=None, min_occurs=1, max_occurs=1,
                 nillable=False, default=None, is_global=False, attr_name=None):
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
        self.default = default
        self.attr_name = attr_name or self.name
        # assert type_

    def __str__(self):
        if self.type:
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

    @property
    def default_value(self):
        value = [] if self.accepts_multiple else self.default
        return value

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

        """
        context = context or XmlParserContext()
        instance_type = qname_attr(xmlelement, xsi_ns('type'))
        xsd_type = None
        if instance_type:
            xsd_type = schema.get_type(instance_type, fail_silently=True)
        xsd_type = xsd_type or self.type
        return xsd_type.parse_xmlelement(
            xmlelement, schema, allow_none=allow_none, context=context)

    def parse_kwargs(self, kwargs, name, available_kwargs):
        return self.type.parse_kwargs(
            kwargs, name or self.attr_name, available_kwargs)

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        """Consume matching xmlelements and call parse() on each of them"""
        result = []
        num_matches = 0
        for i in max_occurs_iter(self.max_occurs):
            if not xmlelements:
                break

            # Workaround for SOAP servers which incorrectly use unqualified
            # or qualified elements in the responses (#170, #176). To make the
            # best of it we compare the full uri's if both elements have a
            # namespace. If only one has a namespace then only compare the
            # localname.

            # If both elements have a namespace and they don't match then skip
            element_tag = etree.QName(xmlelements[0].tag)
            if (
                element_tag.namespace and self.qname.namespace and
                element_tag.namespace != self.qname.namespace
            ):
                break

            # Only compare the localname
            if element_tag.localname == self.qname.localname:
                xmlelement = xmlelements.popleft()
                num_matches += 1
                item = self.parse(
                    xmlelement, schema, allow_none=True, context=context)
                if item is not None:
                    result.append(item)
            else:
                # If the element passed doesn't match and the current one is
                # not optional then throw an error
                if num_matches == 0 and not self.is_optional:
                    raise UnexpectedElementError(
                        "Unexpected element %r, expected %r" % (
                            element_tag.text, self.qname.text))
                break

        if not self.accepts_multiple:
            result = result[0] if result else None
        return result

    def render(self, parent, value):
        """Render the value(s) on the parent lxml.Element.

        This actually just calls _render_value_item for each value.

        """
        assert parent is not None

        if self.accepts_multiple and isinstance(value, list):
            for val in value:
                self._render_value_item(parent, val)
        else:
            self._render_value_item(parent, value)

    def _render_value_item(self, parent, value):
        """Render the value on the parent lxml.Element"""
        if value is None:
            if self.is_optional:
                return

            elm = etree.SubElement(parent, self.qname)
            if self.nillable:
                elm.set(xsi_ns('nil'), 'true')
            return

        node = etree.SubElement(parent, self.qname)
        xsd_type = getattr(value, '_xsd_type', self.type)

        if xsd_type != self.type:
            return value._xsd_type.render(node, value, xsd_type)
        return self.type.render(node, value)

    def resolve_type(self):
        self.type = self.type.resolve()

    def resolve(self):
        self.resolve_type()
        return self

    def signature(self, depth=()):
        if len(depth) > 0 and self.is_global:
            return self.name + '()'

        value = self.type.signature(depth)
        if self.accepts_multiple:
            return '%s[]' % value
        return value


class Attribute(Element):
    def __init__(self, name, type_=None, required=False, default=None):
        super(Attribute, self).__init__(name=name, type_=type_, default=default)
        self.required = required
        self.array_type = None

    def parse(self, value):
        try:
            return self.type.pythonvalue(value)
        except (TypeError, ValueError):
            logger.exception("Error during xml -> python translation")
            return None

    def render(self, parent, value):
        if value is None and not self.required:
            return

        value = self.type.xmlvalue(value)
        parent.set(self.qname, value)

    def clone(self, *args, **kwargs):
        array_type = kwargs.pop('array_type', None)
        new = super(Attribute, self).clone(*args, **kwargs)
        new.array_type = array_type
        return new

    def resolve(self):
        retval = super(Attribute, self).resolve()
        self.type = self.type.resolve()
        if self.array_type:
            retval.array_type = self.array_type.resolve()
        return retval


class AttributeGroup(Element):
    def __init__(self, name, attributes):
        self.name = name
        self.type = None
        self._attributes = attributes
        super(AttributeGroup, self).__init__(name, is_global=True)

    @property
    def attributes(self):
        result = []
        for attr in self._attributes:
            if isinstance(attr, AttributeGroup):
                result.extend(attr.attributes)
            else:
                result.append(attr)
        return result

    def resolve(self):
        resolved = []
        for attribute in self._attributes:
            value = attribute.resolve()
            assert value is not None
            if isinstance(value, list):
                resolved.extend(value)
            else:
                resolved.append(value)
        self._attributes = resolved
        return self

    def signature(self, depth=()):
        return ', '.join(attr.signature() for attr in self._attributes)


class AnyAttribute(Base):
    name = None

    def __init__(self, process_contents='strict'):
        self.qname = None
        self.process_contents = process_contents

    def parse(self, attributes, context=None):
        return attributes

    def resolve(self):
        return self

    def render(self, parent, value):
        if value is None:
            return

        for name, val in value.items():
            parent.set(name, val)

    def signature(self, depth=()):
        return '{}'


class RefElement(object):

    def __init__(self, tag, ref, schema, is_qualified=False,
                 min_occurs=1, max_occurs=1):
        self._ref = ref
        self._is_qualified = is_qualified
        self._schema = schema
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs

    def resolve(self):
        elm = self._schema.get_element(self._ref)
        elm = elm.clone(
            elm.qname, min_occurs=self.min_occurs, max_occurs=self.max_occurs)
        return elm.resolve()


class RefAttribute(RefElement):
    def __init__(self, *args, **kwargs):
        self._array_type = kwargs.pop('array_type', None)
        super(RefAttribute, self).__init__(*args, **kwargs)

    def resolve(self):
        attrib = self._schema.get_attribute(self._ref)
        attrib = attrib.clone(attrib.qname, array_type=self._array_type)
        return attrib.resolve()


class RefAttributeGroup(RefElement):
    def resolve(self):
        value = self._schema.get_attribute_group(self._ref)
        return value.resolve()


class RefGroup(RefElement):
    def resolve(self):
        return self._schema.get_group(self._ref)
