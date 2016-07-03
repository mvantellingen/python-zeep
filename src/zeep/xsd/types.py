from collections import OrderedDict

import six
from cached_property import threaded_cached_property

from zeep.xsd.elements import Element
from zeep.xsd.indicators import Sequence
from zeep.xsd.utils import UniqueAttributeName
from zeep.xsd.valueobjects import CompoundValue


class Type(object):
    name = None

    def __init__(self):
        self._resolved = False

    def accept(self, value):
        raise NotImplementedError

    def parse_xmlelement(self, xmlelement, schema=None):
        raise NotImplementedError

    def parsexml(self, xml, schema=None):
        raise NotImplementedError

    def render(self, parent, value):
        raise NotImplementedError

    def resolve(self):
        raise NotImplementedError

    @property
    def attributes(self):
        return []

    @classmethod
    def signature(cls, depth=0):
        return ''


class UnresolvedType(Type):
    def __init__(self, qname, schema):
        self.qname = qname
        self.schema = schema

    def __repr__(self):
        return '<%s(qname=%r)>' % (self.__class__.__name__, self.qname)

    def resolve(self):
        retval = self.schema.get_type(self.qname)
        return retval.resolve()


class UnresolvedCustomType(Type):

    def __init__(self, name, base_qname, schema):
        assert name is not None
        self.name = name
        self.schema = schema
        self.base_qname = base_qname

    def resolve(self):
        base = self.base_qname
        if isinstance(self.base_qname, (UnresolvedType, self.__class__)):
            base = base.resolve()

        cls_attributes = {
            '__module__': 'zeep.xsd.dynamic_types',
        }
        xsd_type = type(self.name, (base.__class__,), cls_attributes)
        return xsd_type()


@six.python_2_unicode_compatible
class SimpleType(Type):

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

    def __eq__(self, other):
        return (
            other is not None and
            self.__class__ == other.__class__ and
            self.__dict__ == other.__dict__)

    def __str__(self):
        return self.name

    def parse_xmlelement(self, xmlelement, schema=None):
        if xmlelement.text is None:
            return
        return self.pythonvalue(xmlelement.text)

    def pythonvalue(self, xmlvalue):
        raise NotImplementedError(
            '%s.pytonvalue() not implemented' % self.__class__.__name__)

    def render(self, parent, value):
        parent.text = self.xmlvalue(value)

    def resolve(self):
        return self

    @classmethod
    def signature(cls, depth=0):
        return cls.name

    def xmlvalue(self, value):
        raise NotImplementedError(
            '%s.xmlvalue() not implemented' % self.__class__.__name__)


class ComplexType(Type):
    _xsd_name = None
    _xsd_base = None

    def __init__(self, element=None, attributes=None,
                 restriction=None, extension=None, qname=None):
        if element and type(element) == list:
            element = Sequence(element)

        self.name = self.__class__.__name__ if qname else None
        self._element = element
        self._attributes = attributes or []
        self._restriction = restriction
        self._extension = extension

        super(ComplexType, self).__init__()

    def __call__(self, *args, **kwargs):
        if not hasattr(self, '_value_class'):
            self._value_class = type(
                self.__class__.__name__, (CompoundValue,),
                {'_xsd_type': self, '__module__': 'zeep.objects'})

        return self._value_class(*args, **kwargs)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self.signature())

    @threaded_cached_property
    def attributes(self):
        result = []
        if self._extension and hasattr(self._extension, 'attributes'):
            result.extend(self._extension.attributes)

        elm_names = {name for name, elm in self.elements if name is not None}
        attrs = []
        for attr in self._attributes:
            if attr.name in elm_names:
                name = 'attr__%s' % attr.name
            else:
                name = attr.name
            attrs.append((name, attr))
        result.extend(attrs)
        return result

    @threaded_cached_property
    def elements(self):
        """List of tuples containing the element name and the element"""
        result = []
        for name, element in self.elements_nested:
            if isinstance(element, Element):
                result.append((element.name, element))
            else:
                result.extend(element.elements)
        return result

    @threaded_cached_property
    def elements_nested(self):
        """List of tuples containing the element name and the element"""
        result = []
        generator = UniqueAttributeName()

        if self._extension:
            name = generator.get_name()
            if not hasattr(self._extension, 'elements_nested'):
                result.append((name, Element(name, self._extension)))
            else:
                result.extend(self._extension.elements_nested)
        # _element is one of All, Choice, Group, Sequence
        if self._element:
            result.append((generator.get_name(), self._element))
        return result

    def parse_xmlelement(self, xmlelement, schema):
        init_kwargs = OrderedDict()

        elements = xmlelement.getchildren()
        attributes = xmlelement.attrib
        if not elements and not attributes:
            return None  # object is nil

        # Parse attributes
        for name, attribute in self.attributes:
            value = attributes.get(attribute.qname.text)
            init_kwargs[name] = attribute.parse(value)

        # Parse elements
        children = xmlelement.getchildren()
        for name, element in self.elements_nested:
            result = element.parse_xmlelements(children, schema, name)
            init_kwargs.update(result)

        return self(**init_kwargs)

    def render(self, parent, value, xsd_type=None):
        for name, attribute in self.attributes:
            attr_value = getattr(value, name, None)
            attribute.render(parent, attr_value)

        for name, element in self.elements_nested:
            if isinstance(element, Element):
                element.type.render(parent, getattr(value, name))
            else:
                element.render(parent, value)

        if xsd_type and xsd_type._xsd_name:
            parent.set(
                '{http://www.w3.org/2001/XMLSchema-instance}type',
                xsd_type._xsd_name)

    def resolve(self):
        """ EXTENDS / RESTRICTS """
        if self._resolved:
            return self
        self._resolved = True

        if self._extension:
            self._extension = self._extension.resolve()

        if self._restriction:
            self._restriction = self._restriction.resolve()

        if self._element:
            self._element = self._element.resolve()

        for i, attribute in enumerate(self._attributes):
            self._attributes[i] = attribute.resolve()
            assert self._attributes[i] is not None
        return self

    def signature(self, depth=0):
        if depth > 5:
            return '<recursive>'
        parts = []

        depth += 1
        for name, element in self.elements_nested:
            # http://schemas.xmlsoap.org/soap/encoding/ contains cyclic type
            if isinstance(element, Element) and element.type == self:
                continue

            part = element.signature(depth)
            parts.append(part)

        for name, attribute in self.attributes:
            part = '%s: %s' % (name, attribute.signature(depth))
            parts.append(part)

        value = ', '.join(parts)
        if depth > 2:
            value = '{%s}' % value
        return value


class ListType(Type):
    def __init__(self, item_type):
        self.item_type = item_type
        super(ListType, self).__init__()

    def render(self, parent, value):
        parent.text = self.xmlvalue(value)

    def resolve(self):
        self.item_type = self.item_type.resolve()
        return self

    def xmlvalue(self, value):
        item_type = self.item_type
        return ' '.join(item_type.xmlvalue(v) for v in value)


class UnionType(Type):

    def __init__(self, item_types):
        self.item_types = item_types
        super(UnionType, self).__init__()

    def resolve(self):
        self.item_types = [item.resolve() for item in self.item_types]
        return self

    def signature(self, depth=0):
        return ''
