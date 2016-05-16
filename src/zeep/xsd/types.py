import pprint
from collections import OrderedDict

import six

from zeep.utils import process_signature
from zeep.xsd.elements import (
    Any, Attribute, Choice, Element, GroupElement, ListElement, RefElement)


class Type(object):

    def accept(self, value):
        raise NotImplementedError

    def parse_xmlelement(self, xmlelement):
        raise NotImplementedError

    def parsexml(self, xml):
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
        retval.resolve(schema)
        return retval


class SimpleType(Type):

    def __eq__(self, other):
        return (
            other is not None and
            self.__class__ == other.__class__ and
            self.__dict__ == other.__dict__)

    def render(self, parent, value):
        parent.text = self.xmlvalue(value)

    def parse_xmlelement(self, xmlelement):
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

    def properties(self):
        return list(self._children)

    def fields(self):
        """Return a list of tuples containing the name and element of the
        fields.

        """
        result = []
        num = 1
        for prop in self._children:
            if isinstance(prop, Choice):
                for elm in prop.elements:
                    result.append((elm.name, elm, prop))
            elif isinstance(prop, Any):
                result.append(('_any_%d' % num, prop, None))
                num += 1
            elif prop.name is None:
                result.append(('_value', prop, None))
            else:
                result.append((prop.name, prop, None))
        return result

    def serialize(self, value):
        return OrderedDict([
            (field.name, field.serialize(getattr(value, field.name, None)))
            for field in self.properties()
        ])

    def render(self, parent, value):
        for name, element, container in self.fields():
            sub_value = getattr(value, name, None)

            if container and isinstance(container, Choice):
                if isinstance(sub_value, list):
                    for item in sub_value:
                        element.render(parent, item)
                elif sub_value is not None:
                    element.render(parent, sub_value)
            else:
                element.render(parent, sub_value)

    def __call__(self, *args, **kwargs):
        if not hasattr(self, '_value_class'):
            self._value_class = type(
                self.__class__.__name__, (CompoundValue,),
                {'_xsd_type': self, '__module__': 'zeep.objects'})

        return self._value_class(*args, **kwargs)

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
        containers = set()
        for name, element, container in self.fields():
            if container is None:
                parts.append(element._signature(name))
            elif container not in containers:
                parts.append(container._signature())
                containers.add(container)

        return ', '.join(parts)

    def parse_xmlelement(self, xmlelement):
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
            value = field.parse(value)
            setattr(instance, key, value)

        fields = iter(f for f in fields if not isinstance(f, Attribute))
        field = next(fields)
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

            result = field.parse(element)
            if isinstance(field, ListElement):
                getattr(instance, field.name).append(result)
            else:
                setattr(instance, field.name, result)

        return instance

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self.signature())


class CompoundValue(object):

    def __init__(self, *args, **kwargs):
        fields = self._xsd_type.fields()

        # Set default values
        for key, value, container in fields:
            if isinstance(value, ListElement):
                value = []
            else:
                value = None
            setattr(self, key, value)

        items = process_signature(fields, args, kwargs)
        fields = OrderedDict([(name, elm) for name, elm, container in fields])
        for key, value in items.items():
            field = fields[key]

            if isinstance(field, Any) and not isinstance(value, AnyObject):
                raise TypeError(
                    "%s: expected AnyObject, %s found" % (
                        key, type(value).__name__))

            if isinstance(value, dict):
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
