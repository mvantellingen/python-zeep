import copy
from collections import OrderedDict

import six
from cached_property import threaded_cached_property

from zeep.exceptions import XMLParseError
from zeep.xsd.const import xsi_ns
from zeep.xsd.elements import Any, AttributeGroup, Element
from zeep.xsd.indicators import Sequence
from zeep.xsd.utils import NamePrefixGenerator
from zeep.xsd.valueobjects import CompoundValue


class Type(object):

    def __init__(self, qname=None, is_global=False):
        self.qname = qname
        self.name = qname.localname if qname else None
        self._resolved = False
        self.is_global = is_global

    def accept(self, value):
        raise NotImplementedError

    def parse_kwargs(self, kwargs, name=None):
        value = None
        name = name or self.name

        if name in kwargs:
            value = kwargs.pop(name)
            return {name: value}, kwargs
        return {}, kwargs

    def parse_xmlelement(self, xmlelement, schema=None, allow_none=True,
                         context=None):
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
        assert self.qname.text != 'None'
        self.schema = schema

    def __repr__(self):
        return '<%s(qname=%r)>' % (self.__class__.__name__, self.qname)

    def render(self, parent, value):
        raise RuntimeError(
            "Unable to render unresolved type %s. This is probably a bug." % (
                self.qname))

    def resolve(self):
        retval = self.schema.get_type(self.qname)
        return retval.resolve()


class UnresolvedCustomType(Type):

    def __init__(self, qname, base_type, schema):
        assert qname is not None
        self.qname = qname
        self.name = str(qname.localname)
        self.schema = schema
        self.base_type = base_type

    def __repr__(self):
        return '<%s(qname=%r, base_type=%r)>' % (
            self.__class__.__name__, self.qname.text, self.base_type)

    def resolve(self):
        base = self.base_type
        base = base.resolve()

        cls_attributes = {
            '__module__': 'zeep.xsd.dynamic_types',
        }

        if issubclass(base.__class__, SimpleType):
            xsd_type = type(self.name, (base.__class__,), cls_attributes)
            return xsd_type(self.qname)

        else:
            xsd_type = type(self.name, (base.base_class,), cls_attributes)
            return xsd_type(self.qname)


@six.python_2_unicode_compatible
class SimpleType(Type):

    def __call__(self, *args, **kwargs):
        """Return the xmlvalue for the given value.

        Expects only one argument 'value'.  The args, kwargs handling is done
        here manually so that we can return readable error messages instead of
        only '__call__ takes x arguments'

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
        return '%s(value)' % (self.__class__.__name__)

    def parse_xmlelement(self, xmlelement, schema=None, allow_none=True,
                         context=None):
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

    def signature(self, depth=0):
        return self.name

    def xmlvalue(self, value):
        raise NotImplementedError(
            '%s.xmlvalue() not implemented' % self.__class__.__name__)


class ComplexType(Type):
    _xsd_name = None

    def __init__(self, element=None, attributes=None,
                 restriction=None, extension=None, qname=None, is_global=False):
        if element and type(element) == list:
            element = Sequence(element)

        self.name = self.__class__.__name__ if qname else None
        self._element = element
        self._attributes = attributes or []
        self._restriction = restriction
        self._extension = extension
        super(ComplexType, self).__init__(qname=qname, is_global=is_global)

    def __call__(self, *args, **kwargs):
        return self._value_class(*args, **kwargs)

    @threaded_cached_property
    def _value_class(self):
        return type(
            self.__class__.__name__, (CompoundValue,),
            {'_xsd_type': self, '__module__': 'zeep.objects'})

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self.signature())

    @threaded_cached_property
    def attributes(self):
        generator = NamePrefixGenerator(prefix='_attr_')
        result = []
        if self._extension and hasattr(self._extension, 'attributes'):
            result.extend(self._extension.attributes)

        if self._restriction and hasattr(self._restriction, 'attributes'):
            pass

        elm_names = {name for name, elm in self.elements if name is not None}
        attributes = []
        for attr in self._attributes:
            if isinstance(attr, AttributeGroup):
                attributes.extend(attr.attributes)
            else:
                attributes.append(attr)

        for attr in attributes:
            if attr.name is None:
                name = generator.get_name()
            elif attr.name in elm_names:
                name = 'attr__%s' % attr.name
            else:
                name = attr.name
            result.append((name, attr))
        return result

    @threaded_cached_property
    def elements(self):
        """List of tuples containing the element name and the element"""
        result = []
        for name, element in self.elements_nested:
            if isinstance(element, Element):
                result.append((element.attr_name, element))
            else:
                result.extend(element.elements)
        return result

    @threaded_cached_property
    def elements_nested(self):
        """List of tuples containing the element name and the element"""
        result = []
        generator = NamePrefixGenerator()

        if self._extension:
            name = generator.get_name()
            if not hasattr(self._extension, 'elements_nested'):
                result.append((name, Element(name, self._extension)))
            else:
                result.extend(self._extension.elements_nested)

        if self._restriction and not self._element:
            # So this is a workaround to support wsdl:arrayType. This doesn't
            # actually belong here but for now it's the easiest way to achieve
            # this. What this does it that is checks if the restriction
            # contains an arrayType attribute and then use that to retrieve
            # the xsd type for the array. (We ignore AnyAttributes here)
            attrs = {attr.qname.text: attr for attr in self._attributes if attr.qname}
            array_type = attrs.get('{http://schemas.xmlsoap.org/soap/encoding/}arrayType')
            if array_type:
                name = generator.get_name()
                result.append((name, Sequence([
                    Any(max_occurs='unbounded', restrict=array_type.array_type)
                ])))
            else:
                name = generator.get_name()
                if not hasattr(self._restriction, 'elements_nested'):
                    result.append((name, Element(name, self._restriction)))
                else:
                    result.extend(self._restriction.elements_nested)

        # _element is one of All, Choice, Group, Sequence
        if self._element:
            result.append((generator.get_name(), self._element))
        return result

    def parse_xmlelement(self, xmlelement, schema, allow_none=True,
                         context=None):
        """Consume matching xmlelements and call parse() on each"""
        # If this is an empty complexType (<xsd:complexType name="x"/>)
        if not self.attributes and not self.elements:
            return None

        attributes = xmlelement.attrib
        init_kwargs = OrderedDict()

        # If this complexType extends a simpleType then we have no nested
        # elements. Parse it directly via the type object. This is the case
        # for xsd:simpleContent
        if isinstance(self._extension, (SimpleType, UnionType)):
            name, element = self.elements_nested[0]
            init_kwargs[name] = element.type.parse_xmlelement(
                xmlelement, schema, name, context=context)
        else:
            elements = xmlelement.getchildren()
            if allow_none and len(elements) == 0 and len(attributes) == 0:
                return

            # Parse elements. These are always indicator elements (all, choice,
            # group, sequence)
            for name, element in self.elements_nested:
                result = element.parse_xmlelements(
                    elements, schema, name, context=context)
                if result:
                    init_kwargs.update(result)

            # Check if all children are consumed (parsed)
            if elements:
                raise XMLParseError("Unexpected element %r, expected %r" % (
                    elements[0].tag, self.elements[0][1].qname.text))

        # Parse attributes
        attributes = copy.copy(attributes)
        for name, attribute in self.attributes:
            if attribute.name:
                if attribute.qname.text in attributes:
                    value = attributes.pop(attribute.qname.text)
                    init_kwargs[name] = attribute.parse(value)
            else:
                init_kwargs[name] = attribute.parse(attributes)

        return self(**init_kwargs)

    def render(self, parent, value, xsd_type=None):
        """Serialize the given value lxml.Element subelements on the parent
        element.

        """
        if not self.elements_nested and not self.attributes:
            return

        # Render attributes
        for name, attribute in self.attributes:
            attr_value = getattr(value, name, None)
            attribute.render(parent, attr_value)

        # Render sub elements
        for name, element in self.elements_nested:
            if isinstance(element, Element) or element.accepts_multiple:
                element_value = getattr(value, name, None)
            else:
                element_value = value

            if isinstance(element, Element):
                element.type.render(parent, element_value)
            else:
                element.render(parent, element_value)

        if xsd_type and xsd_type._xsd_name:
            parent.set(xsi_ns('type'), xsd_type._xsd_name)

    def parse_kwargs(self, kwargs, name=None):
        value = None
        name = name or self.name

        if name in kwargs:
            value = kwargs.pop(name)
            value = self._create_object(value, name)
            return {name: value}, kwargs
        return {}, kwargs

    def _create_object(self, value, name):
        """Return the value as a CompoundValue object"""
        if value is None:
            return None

        if isinstance(value, list):
            return [self._create_object(val, name) for val in value]

        if isinstance(value, CompoundValue):
            return value

        if isinstance(value, dict):
            return self(**value)

        # Check if the valueclass only expects one value, in that case
        # we can try to automatically create an object for it.
        if len(self.attributes) + len(self.elements) == 1:
            return self(value)

        raise ValueError((
            "Error while create XML for complexType '%s': "
            "Expected instance of type %s, received %r instead."
        ) % (self.qname or name, self._value_class, type(value)))

    def resolve(self):
        """Resolve all sub elements and types"""
        if self._resolved:
            return self
        self._resolved = True

        if self._extension:
            self._extension = self._extension.resolve()
            assert self._extension

        if self._restriction:
            self._restriction = self._restriction.resolve()
            assert self._restriction

        if self._element:
            self._element = self._element.resolve()

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

    def signature(self, depth=0):
        if depth > 0 and self.is_global:
            return self.name

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
        if depth > 1:
            value = '{%s}' % value
        return value


class ListType(Type):
    """Space separated list of simpleType values"""

    def __init__(self, item_type):
        self.item_type = item_type
        super(ListType, self).__init__(None)

    def render(self, parent, value):
        parent.text = self.xmlvalue(value)

    def resolve(self):
        self.item_type = self.item_type.resolve()
        self.base_class = self.item_type.__class__
        return self

    def xmlvalue(self, value):
        item_type = self.item_type
        return ' '.join(item_type.xmlvalue(v) for v in value)

    def pythonvalue(self, value):
        if not value:
            return []
        item_type = self.item_type
        return [item_type.pythonvalue(v) for v in value.split()]

    def signature(self, depth=0):
        return self.item_type.signature(depth) + '[]'


class UnionType(Type):

    def __init__(self, item_types):
        self.item_types = item_types
        assert item_types
        super(UnionType, self).__init__(None)

    def resolve(self):
        self.item_types = [item.resolve() for item in self.item_types]
        self.base_class = self.item_types[0].__class__
        return self

    def signature(self, depth=0):
        return ''

    def parse_xmlelement(self, xmlelement, schema, name=None, context=None):
        for item_type in self.item_types:
            return item_type.parse_xmlelement(xmlelement, schema, name, context)
