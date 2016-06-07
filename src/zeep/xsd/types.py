import pprint
from collections import OrderedDict

import six

from zeep.utils import process_signature
from zeep.xsd.elements import (
    Any, Attribute, Choice, Element, GroupElement, ListElement, RefElement)


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


class SimpleType(Type):

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
        if args:
            return six.text_type(args[0])
        return u''

    def __str__(self):
        return self.name

    def __unicode__(self):
        return six.text_type(self.name)


class ComplexType(Type):

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
        fields = self.properties()
        if not fields:
            return instance

        elements = xmlelement.getchildren()
        attributes = xmlelement.attrib
        if not elements and not attributes:
            return

        fields_map = {f.name: f for f in fields if isinstance(f, Attribute)}
        for key, value in attributes.items():
            field = fields_map.get(key)
            if not field:
                continue
            value = field.parse(value, schema)
            setattr(instance, key, value)

        fields = iter(f for f in fields if not isinstance(f, Attribute))
        field = next(fields, None)

        # If the type has no child elements (only attributes) then return
        # early
        if not field:
            return instance

        for element in elements:

            # Find matching element
            while field and field.qname != element.tag:
                field = next(fields, None)

            if not field:
                break

            # Element can be optional, so if this doesn't match then assume it
            # was.
            if field.qname != element.tag:
                continue

            result = field.parse(element, schema)
            if isinstance(field, ListElement):
                assert getattr(instance, field.name) is not None
                getattr(instance, field.name).append(result)
            else:
                setattr(instance, field.name, result)

        return instance

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self.signature())


class ListType(object):
    def __init__(self, item_type):
        self.item_type = item_type


class UnionType(object):
    def __init__(self, item_types):
        self.item_types = item_types


class CompoundValue(object):

    def __init__(self, *args, **kwargs):
        fields = self._xsd_type.fields()

        # Set default values
        for key, value in fields:
            if isinstance(value, ListElement):
                value = []
            else:
                value = None
            setattr(self, key, value)

        items = process_signature(fields, args, kwargs)
        fields = OrderedDict([(name, elm) for name, elm in fields])
        for key, value in items.items():

            if key in fields:
                field = fields[key]

                if isinstance(field, Choice):
                    pass

                elif isinstance(value, dict):
                    value = field(**value)

                elif isinstance(value, list):
                    if isinstance(field.type, ComplexType):
                        value = [field.type(**v) for v in value]
                    else:
                        value = [field.type(v) for v in value]

            setattr(self, key, value)

    def __repr__(self):
        return pprint.pformat(self.__dict__, indent=4)


class AnyObject(object):
    def __init__(self, xsd_type, value):
        self.xsd_type = xsd_type
        self.value = value

    def __repr__(self):
        return '<%s(type=%r, value=%r)>' % (
            self.__class__.__name__, self.xsd_type, self.value)
