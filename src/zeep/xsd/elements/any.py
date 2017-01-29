import logging

from lxml import etree

from zeep import exceptions
from zeep.utils import qname_attr
from zeep.xsd.const import xsi_ns, NotSet
from zeep.xsd.elements.base import Base
from zeep.xsd.utils import max_occurs_iter
from zeep.xsd.valueobjects import AnyObject

logger = logging.getLogger(__name__)


__all__ = ['Any', 'AnyAttribute']


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
        from zeep.xsd import AnyType
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

        # If a schema was passed inline then check for a matching one
        qname = etree.QName(xmlelement.tag)
        if context and context.schemas:
            for context_schema in context.schemas:
                if context_schema._has_schema_document(qname.namespace):
                    schema = context_schema
                    break

        # Lookup type via xsi:type attribute
        xsd_type = qname_attr(xmlelement, xsi_ns('type'))
        if xsd_type is not None:
            xsd_type = schema.get_type(xsd_type)
            return xsd_type.parse_xmlelement(xmlelement, schema, context=context)

        # Check if a restrict is used
        if self.restrict:
            return self.restrict.parse_xmlelement(
                xmlelement, schema, context=context)

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

        for _unused in max_occurs_iter(self.max_occurs):
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

    def render(self, parent, value, render_path=None):
        assert parent is not None
        self.validate(value, render_path)

        if self.accepts_multiple and isinstance(value, list):
            from zeep.xsd import AnySimpleType

            if isinstance(self.restrict, AnySimpleType):
                for val in value:
                    node = etree.SubElement(parent, 'item')
                    node.set(xsi_ns('type'), self.restrict.qname)
                    self._render_value_item(node, val, render_path)
            elif self.restrict:
                for val in value:
                    node = etree.SubElement(parent, self.restrict.name)
                    # node.set(xsi_ns('type'), self.restrict.qname)
                    self._render_value_item(node, val, render_path)
            else:
                for val in value:
                    self._render_value_item(parent, val, render_path)
        else:
            self._render_value_item(parent, value, render_path)

    def _render_value_item(self, parent, value, render_path):
        if value is None:  # can be an lxml element
            return

        elif isinstance(value, etree._Element):
            parent.append(value)

        elif self.restrict:
            if isinstance(value, list):
                for val in value:
                    self.restrict.render(parent, val, None, render_path)
            else:
                self.restrict.render(parent, value, None, render_path)
        else:
            if isinstance(value.value, list):
                for val in value.value:
                    value.xsd_elm.render(parent, val, render_path)
            else:
                value.xsd_elm.render(parent, value.value, render_path)

    def validate(self, value, render_path):
        if self.accepts_multiple and isinstance(value, list):

            # Validate bounds
            if len(value) < self.min_occurs:
                raise exceptions.ValidationError(
                    "Expected at least %d items (minOccurs check)" % self.min_occurs)
            if self.max_occurs != 'unbounded' and len(value) > self.max_occurs:
                raise exceptions.ValidationError(
                    "Expected at most %d items (maxOccurs check)" % self.min_occurs)

            for val in value:
                self._validate_item(val, render_path)
        else:
            if not self.is_optional and value in (None, NotSet):
                raise exceptions.ValidationError("Missing element for Any")

            self._validate_item(value, render_path)

    def _validate_item(self, value, render_path):
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

    def resolve(self):
        return self

    def signature(self, schema=None, standalone=True):
        if self.restrict:
            base = self.restrict.name
        else:
            base = 'ANY'

        if self.accepts_multiple:
            return '%s[]' % base
        return base


class AnyAttribute(Base):
    name = None

    def __init__(self, process_contents='strict'):
        self.qname = None
        self.process_contents = process_contents

    def parse(self, attributes, context=None):
        return attributes

    def resolve(self):
        return self

    def render(self, parent, value, render_path=None):
        if value is None:
            return

        for name, val in value.items():
            parent.set(name, val)

    def signature(self, schema=None, standalone=True):
        return '{}'
