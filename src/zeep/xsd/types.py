import copy
import logging
from collections import OrderedDict, deque
from itertools import chain

import six
from cached_property import threaded_cached_property

from zeep.exceptions import XMLParseError, UnexpectedElementError
from zeep.xsd.const import xsi_ns
from zeep.xsd.elements import Any, AnyAttribute, AttributeGroup, Element
from zeep.xsd.indicators import Group, OrderIndicator, Sequence
from zeep.xsd.utils import NamePrefixGenerator
from zeep.utils import get_base_class
from zeep.xsd.valueobjects import CompoundValue


logger = logging.getLogger(__name__)


class Type(object):

    def __init__(self, qname=None, is_global=False):
        self.qname = qname
        self.name = qname.localname if qname else None
        self._resolved = False
        self.is_global = is_global

    def accept(self, value):
        raise NotImplementedError

    def parse_kwargs(self, kwargs, name, available_kwargs):
        value = None
        name = name or self.name

        if name in available_kwargs:
            value = kwargs[name]
            available_kwargs.remove(name)
            return {name: value}
        return {}

    def parse_xmlelement(self, xmlelement, schema=None, allow_none=True,
                         context=None):
        raise NotImplementedError(
            '%s.parse_xmlelement() is not implemented' % self.__class__.__name__)

    def parsexml(self, xml, schema=None):
        raise NotImplementedError

    def render(self, parent, value):
        raise NotImplementedError(
            '%s.render() is not implemented' % self.__class__.__name__)

    def resolve(self):
        raise NotImplementedError(
            '%s.resolve() is not implemented' % self.__class__.__name__)

    def extend(self, child):
        raise NotImplementedError(
            '%s.extend() is not implemented' % self.__class__.__name__)

    def restrict(self, child):
        raise NotImplementedError(
            '%s.restrict() is not implemented' % self.__class__.__name__)

    @property
    def attributes(self):
        return []

    @classmethod
    def signature(cls, depth=()):
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

        if issubclass(base.__class__, UnionType):
            xsd_type = type(self.name, (base.__class__,), cls_attributes)
            return xsd_type(base.item_types)

        elif issubclass(base.__class__, SimpleType):
            xsd_type = type(self.name, (base.__class__,), cls_attributes)
            return xsd_type(self.qname)

        else:
            xsd_type = type(self.name, (base.base_class,), cls_attributes)
            return xsd_type(self.qname)


@six.python_2_unicode_compatible
class SimpleType(Type):
    accepted_types = six.string_types

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
        try:
            return self.pythonvalue(xmlelement.text)
        except (TypeError, ValueError):
            logger.exception("Error during xml -> python translation")
            return None

    def pythonvalue(self, xmlvalue):
        raise NotImplementedError(
            '%s.pytonvalue() not implemented' % self.__class__.__name__)

    def render(self, parent, value):
        parent.text = self.xmlvalue(value)

    def resolve(self):
        return self

    def signature(self, depth=()):
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

    @property
    def accepted_types(self):
        return (self._value_class,)

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
        elm_names = {name for name, elm in self.elements if name is not None}
        for attr in self._attributes_unwrapped:
            if attr.name is None:
                name = generator.get_name()
            elif attr.name in elm_names:
                name = 'attr__%s' % attr.name
            else:
                name = attr.name
            result.append((name, attr))
        return result

    @threaded_cached_property
    def _attributes_unwrapped(self):
        attributes = []
        for attr in self._attributes:
            if isinstance(attr, AttributeGroup):
                attributes.extend(attr.attributes)
            else:
                attributes.append(attr)
        return attributes

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

        # Handle wsdl:arrayType objects
        attrs = {attr.qname.text: attr for attr in self._attributes if attr.qname}
        array_type = attrs.get('{http://schemas.xmlsoap.org/soap/encoding/}arrayType')
        if array_type:
            name = generator.get_name()
            if isinstance(self._element, Group):
                return [(name, Sequence([
                    Any(max_occurs='unbounded', restrict=array_type.array_type)
                ]))]
            else:
                return [(name, self._element)]

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
        if isinstance(self._element, Element) and isinstance(self._element.type, SimpleType):
            name, element = self.elements_nested[0]
            init_kwargs[name] = element.type.parse_xmlelement(
                xmlelement, schema, name, context=context)
        else:
            elements = deque(xmlelement.iterchildren())
            if allow_none and len(elements) == 0 and len(attributes) == 0:
                return

            # Parse elements. These are always indicator elements (all, choice,
            # group, sequence)
            for name, element in self.elements_nested:
                try:
                    result = element.parse_xmlelements(
                        elements, schema, name, context=context)
                    if result:
                        init_kwargs.update(result)
                except UnexpectedElementError as exc:
                    raise XMLParseError(exc.message)

            # Check if all children are consumed (parsed)
            if elements:
                raise XMLParseError("Unexpected element %r" % elements[0].tag)

        # Parse attributes
        if attributes:
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

        if xsd_type:
            if xsd_type._xsd_name:
                parent.set(xsi_ns('type'), xsd_type._xsd_name)
            if xsd_type.qname:
                parent.set(xsi_ns('type'), xsd_type.qname)

    def parse_kwargs(self, kwargs, name, available_kwargs):
        value = None
        name = name or self.name

        if name in available_kwargs:
            value = kwargs[name]
            available_kwargs.remove(name)

            value = self._create_object(value, name)
            return {name: value}
        return {}

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
            return self._resolved
        self._resolved = self

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

        if self._extension:
            self._extension = self._extension.resolve()
            self._resolved = self.extend(self._extension)
            return self._resolved

        elif self._restriction:
            self._restriction = self._restriction.resolve()
            self._resolved = self.restrict(self._restriction)
            return self._resolved

        else:
            return self._resolved

    def extend(self, base):
        """Create a new complextype instance which is the current type
        extending the given base type.

        Used for handling xsd:extension tags

        """
        if isinstance(base, ComplexType):
            base_attributes = base._attributes_unwrapped
            base_element = base._element
        else:
            base_attributes = []
            base_element = None
        attributes = base_attributes + self._attributes_unwrapped

        # Make sure we don't have duplicate (child is leading)
        if base_attributes and self._attributes_unwrapped:
            new_attributes = OrderedDict()
            for attr in attributes:
                if isinstance(attr, AnyAttribute):
                    new_attributes['##any'] = attr
                else:
                    new_attributes[attr.qname.text] = attr
            attributes = new_attributes.values()

        # If the base and the current type both have an element defined then
        # these need to be merged. The base_element might be empty (or just
        # container a placeholder element).
        element = []
        if self._element and base_element:
            element = self._element.clone(self._element.name)
            if isinstance(element, OrderIndicator) and isinstance(base_element, OrderIndicator):
                for item in reversed(base_element):
                    element.insert(0, item)

            elif isinstance(self._element, Group):
                raise NotImplementedError('TODO')
            else:
                pass  # Element (ignore for now)

        elif self._element or base_element:
            element = self._element or base_element
        else:
            element = Element('_value_1', base)

        new = self.__class__(
            element=element,
            attributes=attributes,
            qname=self.qname)
        return new

    def restrict(self, base):
        """Create a new complextype instance which is the current type
        restricted by the base type.

        Used for handling xsd:restriction

        """
        attributes = list(
            chain(base._attributes_unwrapped, self._attributes_unwrapped))

        # Make sure we don't have duplicate (self is leading)
        if base._attributes_unwrapped and self._attributes_unwrapped:
            new_attributes = OrderedDict()
            for attr in attributes:
                if isinstance(attr, AnyAttribute):
                    new_attributes['##any'] = attr
                else:
                    new_attributes[attr.qname.text] = attr
            attributes = new_attributes.values()

        new = self.__class__(
            element=self._element or base._element,
            attributes=attributes,
            qname=self.qname)
        return new.resolve()

    def signature(self, depth=()):
        if len(depth) > 0 and self.is_global:
            return self.name

        parts = []
        depth += (self.name,)
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
        if len(depth) > 1:
            value = '{%s}' % value
        return value


class ListType(SimpleType):
    """Space separated list of simpleType values"""

    def __init__(self, item_type):
        self.item_type = item_type
        super(ListType, self).__init__()

    def __call__(self, value):
        return value

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

    def signature(self, depth=()):
        return self.item_type.signature(depth) + '[]'


class UnionType(SimpleType):

    def __init__(self, item_types):
        self.item_types = item_types
        self.item_class = None
        assert item_types
        super(UnionType, self).__init__(None)

    def resolve(self):
        from zeep.xsd.builtins import _BuiltinType

        self.item_types = [item.resolve() for item in self.item_types]
        base_class = get_base_class(self.item_types)
        if issubclass(base_class, _BuiltinType) and base_class != _BuiltinType:
            self.item_class = base_class
        return self

    def signature(self, depth=()):
        return ''

    def parse_xmlelement(self, xmlelement, schema=None, allow_none=True,
                         context=None):
        if self.item_class:
            return self.item_class().parse_xmlelement(
                xmlelement, schema, allow_none, context)
        return xmlelement.text

    def pythonvalue(self, value):
        if self.item_class:
            return self.item_class().pythonvalue(value)
        return value

    def xmlvalue(self, value):
        if self.item_class:
            return self.item_class().xmlvalue(value)
        return value
