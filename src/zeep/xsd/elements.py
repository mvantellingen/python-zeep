import copy

from lxml import etree

from zeep.utils import qname_attr
from zeep.xsd.context import XmlParserContext
from zeep.xsd.utils import max_occurs_iter


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

    def parse_args(self, args):
        result = {}
        args = copy.copy(args)

        if not args:
            return result, args

        value = args.pop(0)
        return {self.name: value}, args

    def parse_kwargs(self, kwargs, name=None):
        raise NotImplementedError()

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        """Consume matching xmlelements and call parse() on each of them"""
        raise NotImplementedError()

    def signature(self, depth=0):
        return ''


class Any(Base):
    name = None

    def __init__(self, max_occurs=1, min_occurs=1, process_contents='strict'):
        """

        :param process_contents: Specifies how the XML processor should handle
                                 validation against the elements specified by
                                 this any element
        :type process_contents: str (strict, lax, skip)

        """
        self.max_occurs = max_occurs
        self.min_occurs = min_occurs
        self.process_contents = process_contents

        # cyclic import
        from zeep.xsd.builtins import AnyType
        self.type = AnyType()

    def __call__(self, any_object):
        return any_object

    def __repr__(self):
        return '<%s(name=%r)>' % (self.__class__.__name__, self.name)

    def parse(self, xmlelement, schema, context=None):
        if self.process_contents == 'skip':
            return xmlelement

        qname = etree.QName(xmlelement.tag)
        if qname.namespace in context.schemas:
            schema = context.schemas.get(qname.namespace)

        xsd_type = xmlelement.get('{http://www.w3.org/2001/XMLSchema-instance}type')
        if xsd_type is not None:
            element_type = schema.get_type(xsd_type)
            return element_type.parse(xmlelement, schema, context=context)

        try:
            element_type = schema.get_element(xmlelement.tag)
            return element_type.parse(xmlelement, schema, context=context)
        except (ValueError, KeyError):
            return xmlelement

    def parse_kwargs(self, kwargs, name=None):
        if name in kwargs:
            value = kwargs.pop(name)
            return {name: value}, kwargs
        return {}, kwargs

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        """Consume matching xmlelements and call parse() on each of them"""
        result = []

        for i in max_occurs_iter(self.max_occurs):
            if xmlelements:
                xmlelement = xmlelements.pop(0)
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
            for val in value:
                self._render_value_item(parent, val)
        else:
            self._render_value_item(parent, value)

    def _render_value_item(self, parent, value):
        if not value:
            return

        from zeep.xsd.valueobjects import AnyObject  # cyclic import / FIXME

        if not isinstance(value, (etree._Element, AnyObject)):
            raise TypeError((
                "Received object of type %r, " +
                "expected xsd.AnyObject or etree.Element"
            ) % (type(value).__name__))

        if isinstance(value, etree._Element):
            parent.append(value)

        elif isinstance(value.value, list):
            for val in value.value:
                value.xsd_elm.render(parent, val)
        else:
            value.xsd_elm.render(parent, value.value)

    def resolve(self):
        return self

    def signature(self, depth=0):
        if self.accepts_multiple:
            return 'ANY[]'
        return 'ANY'


class Element(Base):
    def __init__(self, name, type_=None, min_occurs=1, max_occurs=1,
                 nillable=False, default=None, is_global=False):
        if name and not isinstance(name, etree.QName):
            name = etree.QName(name)

        self.name = name.localname if name else None
        self.qname = name
        self.type = type_
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.nillable = nillable
        self.is_global = is_global
        self.default = default
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

    def clone(self, name, min_occurs=1, max_occurs=1):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        new = copy.copy(self)
        new.name = name.localname
        new.qname = name
        new.min_occurs = min_occurs
        new.max_occurs = max_occurs
        return new

    def parse(self, xmlelement, schema, allow_none=False, context=None):
        """Process the given xmlelement. If it has an xsi:type attribute then
        use that for further processing. This should only be done for subtypes
        of the defined type but for now we just accept everything.

        """
        context = context or XmlParserContext()
        instance_type = qname_attr(
            xmlelement, '{http://www.w3.org/2001/XMLSchema-instance}type')
        if instance_type:
            xsd_type = schema.get_type(instance_type)
        else:
            xsd_type = self.type
        return xsd_type.parse_xmlelement(
            xmlelement, schema, allow_none=allow_none, context=context)

    def parse_kwargs(self, kwargs, name=None):
        return self.type.parse_kwargs(kwargs, name or self.name)

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        """Consume matching xmlelements and call parse() on each of them"""
        result = []

        for i in max_occurs_iter(self.max_occurs):
            if xmlelements and xmlelements[0].tag == self.qname:
                xmlelement = xmlelements.pop(0)
                item = self.parse(
                    xmlelement, schema, allow_none=True, context=context)
                if item is not None:
                    result.append(item)
            else:
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
            if not self.is_optional:
                etree.SubElement(parent, self.qname)
            return

        if self.name is None:
            return self.type.render(parent, value)

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

    def signature(self, depth=0):
        if depth > 0 and self.is_global:
            return self.name + '()'

        value = self.type.signature(depth)
        if self.accepts_multiple:
            return '%s[]' % value
        return value


class Attribute(Element):
    def __init__(self, name, type_=None, required=False, default=None):
        super(Attribute, self).__init__(name=name, type_=type_, default=default)
        self.required = required

    def parse(self, value):
        return self.type.pythonvalue(value)

    def render(self, parent, value):
        if value is None and not self.required:
            return

        value = self.type.xmlvalue(value)
        parent.set(self.qname, value)


class AnyAttribute(Base):
    name = None

    def __init__(self, process_contents='strict'):
        self.process_contents = process_contents

    def parse(self, attributes, context=None):
        return attributes

    def resolve(self):
        return self

    def render(self, parent, value):
        for name, val in value.items():
            parent.set(name, val)

    def signature(self, depth=0):
        return '{}'


class RefElement(object):

    def __init__(self, tag, ref, schema, min_occurs=1, max_occurs=1):
        self._ref = ref
        self._schema = schema
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs

    def resolve(self):
        elm = self._schema.get_element(self._ref)
        return elm.clone(
            elm.qname, min_occurs=self.min_occurs, max_occurs=self.max_occurs)


class RefAttribute(RefElement):

    def resolve(self):
        return self._schema.get_attribute(self._ref)
