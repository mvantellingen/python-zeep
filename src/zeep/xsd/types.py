import pprint
from collections import OrderedDict

import six

from zeep.utils import process_signature
from zeep.xsd.elements import GroupElement, ListElement, RefElement, Any


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
            if isinstance(prop, Any):
                result.append(('_any_%d' % num, prop))
                num += 1
            else:
                result.append((prop.name, prop))
        return result

    def serialize(self, value):
        return {
            field.name: field.serialize(getattr(value, field.name, None))
            for field in self.properties()
        }

    def render(self, parent, value):
        for name, element in self.fields():
            sub_value = getattr(value, name, None)
            if sub_value is not None:
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
                elm = elm.resolve(schema)
                children.extend(list(elm._children))
            elif isinstance(elm, GroupElement):
                children.extend(list(elm))
            else:
                children.append(elm)
        self._children = children
        return self

    def signature(self):
        return ', '.join([
            '%s%s: %s%s' % (
                name, '=None' if element.is_optional else '',
                element.type.name, '[]' if element.max_occurs != 1 else ''
            )
            for name, element in self.fields()
        ])

    def parse_xmlelement(self, xmlelement):
        instance = self()
        fields = self.properties()
        if not fields:
            return instance

        elements = xmlelement.getchildren()
        fields = iter(fields)
        field = next(fields)
        for element in elements:

            # Find matching element
            while field.qname != element.tag:
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
        for key, value in fields:
            if isinstance(value, ListElement):
                value = []
            else:
                value = None
            setattr(self, key, value)

        fields = OrderedDict(fields)
        items = process_signature(fields.keys(), args, kwargs)
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
