import copy

from lxml import etree

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
        value = None
        name = name or self.name

        if name in kwargs:
            value = kwargs.pop(name)
            return {name: value}, kwargs
        return {}, kwargs

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

    def parse(self, xmlelement, schema):
        if self.process_contents == 'skip':
            return xmlelement

        xsd_type = xmlelement.get('{http://www.w3.org/2001/XMLSchema-instance}type')
        if xsd_type is not None:
            element_type = schema.get_type(xsd_type)
            return element_type.parse(xmlelement, schema)

        try:
            element_type = schema.get_element(xmlelement.tag)
            return element_type.parse(xmlelement, schema)
        except (ValueError, KeyError):
            return xmlelement

    def parse_xmlelements(self, xmlelements, schema, name=None):
        result = []

        for i in max_occurs_iter(self.max_occurs):
            if xmlelements:
                xmlelement = xmlelements.pop(0)
                item = self.parse(xmlelement, schema)
                result.append(item)
            else:
                break

        if self.max_occurs == 1:
            result = result[0] if result else None
        return result

    def render(self, parent, value):
        assert parent is not None
        if not value:
            return

        if isinstance(value.value, list):
            for val in value.value:
                value.xsd_type.render(parent, val)
        else:
            value.xsd_type.render(parent, value.value)

    def resolve(self):
        return self

    def signature(self, depth=0):
        return 'ANY'


class Element(Base):
    def __init__(self, name, type_=None, min_occurs=1, max_occurs=1,
                 nillable=False, default=None):
        if name and not isinstance(name, etree.QName):
            name = etree.QName(name)

        self.name = name.localname if name else None
        self.qname = name
        self.type = type_
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.nillable = nillable
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

    def clone(self, name):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        new = copy.copy(self)
        new.name = name.localname
        new.qname = name
        return new

    def parse(self, xmlelement, schema):
        return self.type.parse_xmlelement(xmlelement, schema)

    def parse_xmlelements(self, xmlelements, schema, name=None):
        result = []

        for i in max_occurs_iter(self.max_occurs):
            if xmlelements and xmlelements[0].tag == self.qname:
                xmlelement = xmlelements.pop(0)
                item = self.parse(xmlelement, schema)
                result.append(item)
            else:
                break

        if self.max_occurs == 1:
            result = result[0] if result else None

        return result

    def render(self, parent, value):
        assert parent is not None
        if self.max_occurs != 1 and isinstance(value, list):
            for val in value:
                self._render_value_item(parent, val)
        else:
            self._render_value_item(parent, value)

    def _render_value_item(self, parent, value):
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
        depth += 1
        if self.type.name:
            value = self.type.name
        else:
            value = self.type.signature(depth)
        if self.accepts_multiple:
            return '%s[]' % value
        return value


class Attribute(Element):
    def __init__(self, name, type_=None, required=False, default=None):
        super(Attribute, self).__init__(name=name, type_=type_, default=default)
        self.required = required

    def parse(self, value, schema=None):
        return self.type.pythonvalue(value)

    def render(self, parent, value):
        if value is None and not self.required:
            return

        value = self.type.xmlvalue(value)
        parent.set(self.qname, value)


class RefElement(object):

    def __init__(self, tag, ref, schema):
        self._ref = ref
        self._schema = schema

    def resolve(self):
        return self._schema.get_element(self._ref)


class RefAttribute(RefElement):

    def resolve(self):
        return self._schema.get_attribute(self._ref)
