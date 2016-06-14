import itertools

from collections import OrderedDict

import six

from zeep.xsd.elements import (
    Any, Attribute, Choice, Element, GroupElement, ListElement, RefElement,
    Sequence)
from zeep.xsd.valueobjects import CompoundValue


class Type(object):

    def accept(self, value):
        raise NotImplementedError

    def parse_xmlelement(self, xmlelement, schema=None):
        raise NotImplementedError

    def parsexml(self, xml, schema=None):
        raise NotImplementedError

    def render(self, parent, value):
        raise NotImplementedError

    def resolve(self, schema):
        raise NotImplementedError

    @classmethod
    def signature(cls):
        return ''


class UnresolvedType(Type):
    def __init__(self, qname):
        self.qname = qname

    def resolve(self, schema):
        retval = schema.get_type(self.qname)
        return retval.resolve(schema)


class UnresolvedCustomType(Type):

    def __init__(self, name, base_qname):
        assert name is not None
        self.name = name
        self.base_qname = base_qname

    def resolve(self, schema):
        base = schema.get_type(self.base_qname)
        base = base.resolve(schema)

        cls_attributes = {
            '__module__': 'zeep.xsd.dynamic_types',
        }
        xsd_type = type(self.name, (base.__class__,), cls_attributes)
        return xsd_type()


@six.python_2_unicode_compatible
class SimpleType(Type):
    name = None

    def __eq__(self, other):
        return (
            other is not None and
            self.__class__ == other.__class__ and
            self.__dict__ == other.__dict__)

    def render(self, parent, value):
        parent.text = self.xmlvalue(value)

    def parse_xmlelement(self, xmlelement, schema=None):
        if xmlelement.text is None:
            return
        return self.pythonvalue(xmlelement.text)

    def xmlvalue(self, value):
        raise NotImplementedError(
            '%s.xmlvalue() not implemented' % self.__class__.__name__)

    def pythonvalue(self, xmlvalue):
        raise NotImplementedError(
            '%s.pytonvalue() not implemented' % self.__class__.__name__)

    def resolve(self, schema):
        return self

    def serialize(self, value):
        return value

    def __call__(self, *args, **kwargs):
        """Return the xmlvalue for the given value.

        The args, kwargs handling is done here manually so that we can return
        readable error messages instead of only '__call__ takes x arguments'

        """
        num_args = len(args) + len(kwargs)
        if num_args != 1:
            raise TypeError((
                '%s() takes exactly 1 argument (%d given). ' +
                'Simple types expect only a single value argument'
            ) % (self.__class__.__name__, num_args))

        if kwargs and 'value' not in kwargs:
            raise TypeError((
                '%s() got an unexpected keyword argument %r. ' +
                'Simple types expect only a single value argument'
            ) % (self.__class__.__name__, next(six.iterkeys(kwargs))))

        value = args[0] if args else kwargs['value']
        return self.xmlvalue(value)

    def __str__(self):
        return self.name

    @classmethod
    def signature(cls):
        return 'value'


class ComplexType(Type):
    name = None

    def __init__(self, children=None):
        self._children = children or []

    def __call__(self, *args, **kwargs):
        if not hasattr(self, '_value_class'):
            self._value_class = type(
                self.__class__.__name__, (CompoundValue,),
                {'_xsd_type': self, '__module__': 'zeep.objects'})

        return self._value_class(*args, **kwargs)

    def properties(self):
        return list(self._children)

    def fields(self):
        """Return a list of tuples containing the name and element of the
        fields.

        """
        result = []
        num_any = 1
        num_choice = 1
        for prop in self._children:
            if isinstance(prop, Any):
                result.append(('_any_%d' % num_any, prop))
                num_any += 1
            elif isinstance(prop, Choice):
                result.append(('_choice_%d' % num_choice, prop))
                num_choice += 1
            elif prop.name is None:
                result.append(('_value', prop))
            else:
                result.append((prop.name, prop))
        return result

    def serialize(self, value):
        return OrderedDict([
            (field.name, field.serialize(getattr(value, field.name, None)))
            for field in self.properties()
        ])

    def render(self, parent, value, xsd_type=None):
        for name, element in self.fields():
            if isinstance(element, Choice):
                element.render(parent, name, value)
            else:
                sub_value = getattr(value, name, None)
                element.render(parent, sub_value)

        if xsd_type:
            parent.set(
                '{http://www.w3.org/2001/XMLSchema-instance}type',
                xsd_type._xsd_name)

    def resolve(self, schema):
        children = []
        for elm in self._children:
            if isinstance(elm, RefElement):
                elm = elm._elm

            if isinstance(elm, UnresolvedType):
                xsd_type = elm.resolve(schema)
                if isinstance(xsd_type, SimpleType):
                    children.append(Element(None, xsd_type))
                else:
                    children.extend(list(xsd_type._children))

            elif isinstance(elm, GroupElement):
                children.extend(list(elm))
            else:
                children.append(elm)
        self._children = children
        return self

    def signature(self):
        parts = []

        for name, element in self.fields():
            part = element.signature(name)
            parts.append(part)
        return ', '.join(parts)

    def parse_xmlelement(self, xmlelement, schema):
        instance = self()
        fields = self.fields()
        if not fields:
            return instance

        elements = xmlelement.getchildren()
        attributes = xmlelement.attrib
        if not elements and not attributes:
            return

        fields_map = {k: v for k, v in fields if isinstance(v, Attribute)}
        for key, value in attributes.items():
            field = fields_map.get(key)
            if not field:
                continue
            value = field.parse(value, schema)
            setattr(instance, key, value)

        fields = iter((k, v) for k, v in fields if not isinstance(v, Attribute))
        field_name, field = next(fields, (None, None))

        # If the type has no child elements (only attributes) then return
        # early
        if not field:
            return instance

        i = 0
        num_elements = len(elements)
        while i < num_elements:
            element = elements[i]
            result = None

            # Find matching element
            while field:
                if isinstance(field, (Choice, Any)):
                    break

                if field.qname == element.tag:
                    break

                field_name, field = next(fields, (None, None))

            if isinstance(field, Choice):
                result = field.parse(elements[i:], schema)
                i += sum(len(choice) for choice in result)

                # If the field has maxOccurs = 1 and is not a sequence then
                # make the interface easier to use by setting the property
                # directly.
                if field.max_occurs == 1:
                    if len(result[0]) == 1:
                        setattr(
                            instance,
                            next(six.iterkeys(result[0])),
                            next(six.itervalues(result[0])))

                setattr(instance, field_name, result)

            elif isinstance(field, Any):
                result = field.parse(element, schema)
                setattr(instance, field_name, result)
                i += 1

            else:
                if not field:
                    raise ValueError("Unexpected element: %r" % element)
                    break

                # Element can be optional, so if this doesn't match then assume
                # it was.
                if field.qname != element.tag:
                    continue

                current_field = field

                result = current_field.parse(element, schema)
                i += 1

                if isinstance(field, ListElement):
                    assert getattr(instance, field.name) is not None
                    getattr(instance, field_name).append(result)
                else:
                    setattr(instance, field_name, result)

            # Check if the next element also applies to the current field
            try:
                if field.max_occurs == 1 or element.tag != elements[i].tag:
                    field_name, field = next(fields, (None, None))
            except IndexError:
                break

        return instance

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self.signature())


class ListType(Type):
    def __init__(self, item_type):
        self.item_type = item_type

    def resolve(self, schema):
        self.item_type = self.item_type.resolve(schema)
        return self

    def xmlvalue(self, value):
        item_type = self.item_type
        return ' '.join(item_type.xmlvalue(v) for v in value)

    def render(self, parent, value):
        parent.text = self.xmlvalue(value)


class UnionType(object):
    def __init__(self, item_types):
        self.item_types = item_types
