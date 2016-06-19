import copy

from lxml import etree

from six.moves import zip_longest


class Base(object):
    _require_keyword_arg = False

    @property
    def is_optional(self):
        return self.min_occurs == 0

    def signature(self, name=None):
        return ''


class Any(Base):
    _require_keyword_arg = False

    def __init__(self, max_occurs=1, min_occurs=1, process_contents='strict'):
        """

        :param process_contents: Specifies how the XML processor should handle
                                 validation against the elements specified by
                                 this any element
        :type process_contents: str (strict, lax, skip)

        """
        self.name = 'any'
        self.max_occurs = max_occurs
        self.min_occurs = min_occurs
        self.process_contents = process_contents

        # cyclic import
        from zeep.xsd.builtins import AnyType
        self.type = AnyType()

    def __repr__(self):
        return '<%s(name=%r)>' % (self.__class__.__name__, self.name)

    def render(self, parent, value):
        assert parent is not None
        if value is None:
            # not possible
            return

        if isinstance(value.value, list):
            for val in value.value:
                value.xsd_type.render(parent, val)
        else:
            value.xsd_type.render(parent, value.value)

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

    def __call__(self, any_object):
        return any_object

    def signature(self, name=None):
        return '%s%s: %s' % (
            name, '=None' if self.is_optional else '',
            '[]' if self.max_occurs != 1 else ''
        )


class Element(Base):
    def __init__(self, name, type_=None, min_occurs=1, max_occurs=1,
                 nillable=False):
        if name and not isinstance(name, etree.QName):
            name = etree.QName(name)

        self.name = name.localname if name else None
        self.qname = name
        self.type = type_
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs
        self.nillable = nillable
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

    def signature(self, name=None):
        assert self.type, '%r has no type' % self
        return '%s%s: %s%s' % (
            name, '=None' if self.is_optional else '',
            self.type.name, '[]' if self.max_occurs != 1 else ''
        )

    def clone(self, name):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        new = copy.copy(self)
        new.name = name.localname
        new.qname = name
        return new

    def serialize(self, value):
        return self.type.serialize(value)

    def resolve_type(self):
        self.type = self.type.resolve()

    def render(self, parent, value):
        assert parent is not None

        if value is None:
            if not self.is_optional:
                node = etree.SubElement(parent, self.qname)
            return

        if self.name is None:
            return self.type.render(parent, value)

        node = etree.SubElement(parent, self.qname)

        xsd_type = getattr(value, '_xsd_type', self.type)
        if xsd_type != self.type:
            return value._xsd_type.render(node, value, xsd_type)
        return self.type.render(node, value)

    def parse(self, value, schema):
        return self.type.parse_xmlelement(value, schema)


class Attribute(Element):
    def __init__(self, name, type_=None, required=False, default=None):
        super(Attribute, self).__init__(name=name, type_=type_)
        self.required = required
        self.default = default or ''

    def render(self, parent, value):
        if value is None:
            if self.default:
                value = self.default
            elif not self.required:
                return
            else:
                value = ""  # XXX Throw exception?

        value = self.type.xmlvalue(value)
        parent.set(self.qname, value)

    def parse(self, value, schema=None):
        return self.type.pythonvalue(value)


class ListElement(Element):

    def __call__(self, *args, **kwargs):
        return [self.type(*args, **kwargs)]

    def serialize(self, value):
        if value:
            return [self.type.serialize(val) for val in value]
        return []

    def render(self, parent, value):
        for val in value:
            super(ListElement, self).render(parent, val)


class GroupElement(Element):
    def __init__(self, *args, **kwargs):
        self.children = kwargs.pop('children', [])
        assert self.children
        assert isinstance(self.children, list)
        super(GroupElement, self).__init__(*args, **kwargs)

    def __iter__(self, *args, **kwargs):
        for item in self.children:
            yield item

    def properties(self):
        return self.children

    def signature(self, name):
        return '%s%s: %s' % (
            name, '=None' if self.is_optional else '',
            '[]' if self.max_occurs != 1 else ''
        )


class Choice(Base):
    _require_keyword_arg = False

    def __init__(self, elements, max_occurs=1, min_occurs=1):
        self.name = 'choice'
        self.type = None
        self.elements = elements
        self.max_occurs = max_occurs
        self.min_occurs = min_occurs

    @property
    def is_optional(self):
        return True

    def key(self):
        # XXX Any elemetns?
        return ':'.join(elm.name for elm in self.elements)

    def render(self, parent, name, value):
        choice_metadata = getattr(value, name)

        if self.max_occurs == 1:
            choice_metadata = [choice_metadata]

        for item in choice_metadata:
            choice_element = self.elements[item.index]

            if isinstance(choice_element, Element):
                choice_value = item.values.get(choice_element.name)
                if choice_value is None and self.is_optional:
                    return

                if isinstance(choice_value, list):
                    for item in choice_value:
                        choice_element.render(parent, item)
                else:
                    choice_element.render(parent, choice_value)
            else:
                for element in choice_element:
                    value = item.values[element.name]
                    if isinstance(value, list):
                        for item in value:
                            element.render(parent, item)
                    else:
                        element.render(parent, value)

    def signature(self, name):
        part = ' | '.join([
            '{%s}' % element.signature(element.name)
            for element in self.elements
        ])

        if self.max_occurs != 1:
            return '%s: [%s]' % (name, part)
        return '%s: %s' % (name, part)

    def parse(self, elements, schema):
        result = []
        i = 0
        for choice_element in elements:
            for iter_field in self.elements:
                if isinstance(iter_field, Sequence):
                    subresult = iter_field.parse(elements[i:], schema)
                    if subresult:
                        i += len(subresult)
                        result.append(subresult)
                        break
                else:
                    if iter_field.qname == choice_element.tag:
                        choice_result = iter_field.parse(choice_element, schema)
                        result.append({
                            iter_field.name: choice_result
                        })
                        i += 1
                        break

            if len(result) >= self.max_occurs:
                break

        return result


class Sequence(list):
    name = 'sequence'
    _require_keyword_arg = False

    def signature(self, name):
        return ', '.join([
            element.signature(element.name) for element in self
        ])

    def parse(self, elements, schema):

        result = {}
        for field, element in zip_longest(self, elements):
            if field is None:
                break

            if element is None and field.is_optional:
                result[field.name] = None
            elif field.qname == element.tag:
                result[field.name] = field.parse(element, schema)
            elif field.is_optional:
                result[field.name] = None
            else:
                return None
        return result


class RefElement(object):

    def __init__(self, tag, ref, schema):
        self._ref = ref
        self._schema = schema

    @property
    def _elm(self):
        return self._schema.get_element(self._ref)

    def __iter__(self, *args, **kwargs):
        elm = self._elm

        if isinstance(elm, (GroupElement, ListElement)):
            for item in elm.properties():
                yield item
        else:
            yield elm

    def __call__(self, *args, **kwargs):
        return self._elm(*args, **kwargs)

    def __getattr__(self, name):
        if not name.startswith('_'):
            return getattr(self._elm, name)

        return getattr(self, name)


class RefAttribute(RefElement):

    @property
    def _elm(self):
        return self._schema.get_attribute(self._ref)
