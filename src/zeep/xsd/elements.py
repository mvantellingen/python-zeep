import copy
import operator
from collections import defaultdict

from lxml import etree

from six.moves import zip_longest
from zeep.xsd.utils import UniqueAttributeName, max_occurs_iter


class Base(object):

    @property
    def accepts_multiple(self):
        return self.max_occurs != 1

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

    def signature(self):
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

    def signature(self):
        return 'ANY'


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

    def serialize(self, value):
        if self.max_occurs == 1:
            return self.type.serialize(value)
        else:
            if value:
                return [self.type.serialize(val) for val in value]
            return []

    def signature(self):
        if self.max_occurs != 1:
            return '%s[]' % self.type.signature()
        return self.type.signature()


class Attribute(Element):
    def __init__(self, name, type_=None, required=False, default=None):
        super(Attribute, self).__init__(name=name, type_=type_)
        self.required = required
        self.default = default or ''

    def parse(self, value, schema=None):
        return self.type.pythonvalue(value)

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


class Group(Base):
    """Groups a set of element declarations so that they can be incorporated as
    a group into complex type definitions.

    """

    def __init__(self, name, child, max_occurs=1, min_occurs=1):
        self.child = child
        self.qname = name
        self.name = name.localname
        self.max_occurs = max_occurs
        self.min_occurs = min_occurs

    def __iter__(self, *args, **kwargs):
        for item in self.child:
            yield item

    @property
    def elements(self):
        if self.accepts_multiple:
            return [('_value_1', self.child)]
        return self.child.elements

    def parse_args(self, args):
        return self.child.parse_args(args)

    def parse_kwargs(self, kwargs, name=None):
        if self.accepts_multiple:
            if name not in kwargs:
                return {}, kwargs

            item_kwargs = kwargs.pop(name)
            result = []
            sub_name = '_value_1' if self.child.accepts_multiple else None
            for i, sub_kwargs in zip(max_occurs_iter(self.max_occurs), item_kwargs):
                subresult, res_kwargs = self.child.parse_kwargs(sub_kwargs, sub_name)
                if subresult:
                    result.append(subresult)
            if result:
                result = {name: result}
        else:
            result, kwargs = self.child.parse_kwargs(kwargs, name)
        return result, kwargs

    def parse_xmlelements(self, xmlelements, schema, name=None):
        result = []

        for i in max_occurs_iter(self.max_occurs):
            result.append(
                self.child.parse_xmlelements(xmlelements, schema, name)
            )
        if self.max_occurs == 1 and result:
            return result[0]
        return {name: result}

    def render(self, *args, **kwargs):
        return self.child.render(*args, **kwargs)

    def resolve(self):
        self.child = self.child.resolve()
        return self

    def signature(self):
        return ''


class Container(Base, list):
    name = None

    def __repr__(self):
        return '<%s(%s)>' % (
            self.__class__.__name__, super(Container, self).__repr__())

    def __init__(self, elements=None, min_occurs=1, max_occurs=1):
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs

        if elements is None:
            super(Container, self).__init__()
        else:
            super(Container, self).__init__(elements)

    @property
    def elements(self):
        """List of tuples containing the element name and the element"""
        result = []
        for name, elm in self.elements_nested:
            if name is None:
                result.extend(elm.elements)
            else:
                result.append((name, elm))
        return result

    @property
    def elements_nested(self):
        """List of tuples containing the element name and the element"""
        result = []
        generator = UniqueAttributeName()
        for elm in self:
            if isinstance(elm, (All, Group, Sequence)):
                if elm.accepts_multiple:
                    result.append((generator.get_name(), elm))
                else:
                    result.append((None, elm))
            elif isinstance(elm, (Any, Choice)):
                result.append((generator.get_name(), elm))
            else:
                result.append((elm.name, elm))
        return result

    @property
    def is_optional(self):
        return self.min_occurs == 0

    def accept(self, values):
        required_keys = {
            name for name, element in self.elements
            if not element.is_optional
        }
        optional_keys = {
            name for name, element in self.elements
            if element.is_optional
        }

        from zeep.xsd.valueobjects import CompoundValue
        if isinstance(values, CompoundValue):
            values_keys = set(values.__dict__.keys())
            values_keys.remove('_xsd_elm')
        else:
            values_keys = set(values.keys())

        if (
            values_keys <= (required_keys | optional_keys) and
            required_keys <= values_keys
        ):
            return True
        return False

    def parse_args(self, args):
        result = {}
        args = copy.copy(args)

        for name, element in self.elements:
            if not args:
                break
            arg = args.pop(0)
            result[name] = arg

        return result, args

    def parse_kwargs(self, kwargs, name=None):
        """Apply the given kwarg to the element.

        Returns a tuple with two dictionaries, the first one being the result
        and the second one the unparsed kwargs.

        """
        if self.accepts_multiple:
            assert name

        if name and name in kwargs:

            # Make sure we have a list, lame lame
            item_kwargs = kwargs.get(name)
            if not isinstance(item_kwargs, list):
                item_kwargs = [item_kwargs]

            result = []
            for i, item_value in zip(max_occurs_iter(self.max_occurs), item_kwargs):
                subresult = {}
                for item_name, element in self.elements:
                    value, item_value = element.parse_kwargs(item_value, item_name)
                    if value is not None:
                        subresult.update(value)

                result.append(subresult)

            if self.max_occurs == 1:
                result = result[0] if result else None
            else:
                result = {name: result}

            # All items consumed
            if not any(filter(None, item_kwargs)):
                del kwargs[name]

            return result, kwargs

        else:
            result = {}
            for elm_name, element in self.elements:
                sub_result, kwargs = element.parse_kwargs(kwargs, elm_name)
                if sub_result is not None:
                    result.update(sub_result)

            if name:
                result = {name: result}

            return result, kwargs

    def resolve(self):
        for i, elm in enumerate(self):
            if isinstance(elm, RefElement):
                elm = elm.resolve()
            self[i] = elm
        return self

    def render(self, parent, value):
        if not isinstance(value, list):
            values = [value]
        else:
            values = value

        for i, value in zip(max_occurs_iter(self.max_occurs), values):
            for name, element in self.elements_nested:

                if name:
                    if isinstance(value, dict):
                        element_value = value.get(name)
                    else:
                        element_value = getattr(value, name, None)
                else:
                    element_value = value

                if element_value is not None or not element.is_optional:
                    element.render(parent, element_value)

    def serialize(self, value):
        return value

    def signature(self):
        parts = []
        for name, element in self.elements_nested:
            if name:
                parts.append('%s: %s' % (name, element.signature()))
            elif isinstance(element, Container):
                parts.append('%s' % (element.signature()))
            else:
                parts.append('%s: %s' % (name, element.signature()))
        part = ', '.join(parts)

        if self.accepts_multiple:
            return '[%s]' % (part)
        return part



class All(Container):
    """Allows the elements in the group to appear (or not appear) in any order
    in the containing element.

    """

    def parse_xmlelements(self, xmlelements, schema, name=None):
        result = {}

        values = defaultdict(list)
        for elm in xmlelements:
            values[elm.tag].append(elm)

        for name, element in self.elements:
            sub_elements = values.get(element.qname)
            if sub_elements:
                result[name] = element.parse_xmlelements(sub_elements, schema)

        return result


class Choice(Container):

    @property
    def is_optional(self):
        return True

    def parse_xmlelements(self, xmlelements, schema, name=None):
        result = []

        for i in max_occurs_iter(self.max_occurs):
            for node in list(xmlelements):

                # Choose out of multiple
                options = []
                for name, element in self.elements_nested:

                    local_xmlelements = copy.copy(xmlelements)
                    sub_result = element.parse_xmlelements(local_xmlelements, schema)

                    if isinstance(element, Container):
                        if element.accepts_multiple:
                            sub_result = {name: sub_result}
                    else:
                        sub_result = {name: sub_result}

                    num_consumed = len(xmlelements) - len(local_xmlelements)
                    if num_consumed:
                        options.append((num_consumed, sub_result))

                # Sort on least left
                options = sorted(options, key=operator.itemgetter(0))[::-1]
                if options:
                    result.append(options[0][1])
                    for i in range(options[0][0]):
                        xmlelements.pop(0)
                else:
                    break

        if not self.accepts_multiple:
            result = result[0] if result else None

        return result

    def parse_kwargs(self, kwargs, name):
        """Processes the kwargs for this choice element.

        Returns a tuple containing value, kwags.

        This handles two distinct initialization methods:

        1. Passing the choice elements directly to the kwargs (unnested)
        2. Passing the choice elements into the `name` kwarg (_alue_1) (nested).
           This case is required when multiple choice elements are given.

        :param name: Name of the choice element (_value_1)
        :type name: str
        :param element: Choice element object
        :type element: zeep.xsd.Choice
        :param kwargs: dict (or list of dicts) of kwargs for initialization
        :type kwargs: list / dict

        """
        result = []
        kwargs = copy.copy(kwargs)

        if name and name in kwargs:
            values = kwargs.pop(name)
            if isinstance(values, dict):
                values = [values]

            for value in values:
                for element in self:

                    # TODO: Use most greedy choice instead of first matching
                    if isinstance(element, Container):
                        choice_value = value[name] if name in value else value
                        if element.accept(choice_value):
                            result.append(choice_value)
                            break
                    else:
                        if element.name in value:
                            choice_value = value.get(element.name)
                            result.append({element.name: choice_value})
                            break
                else:
                    raise TypeError(
                        "No complete xsd:Sequence found for the xsd:Choice %r.\n"
                        "The signature is: %s" % (name, self.signature()))

            if not self.accepts_multiple:
                result = result[0] if result else None
        else:
            # Direct use-case isn't supported when maxOccurs > 1
            if self.accepts_multiple:
                return {}, kwargs

            # When choice elements are specified directly in the kwargs
            org_kwargs = kwargs
            for choice in self:
                result, kwargs = choice.parse_kwargs(org_kwargs)
                if result:
                    break
            else:
                result = {}
                kwargs = org_kwargs

        if name:
            result = {name: result}
        return result, kwargs

    def render(self, parent, value):
        if self.max_occurs == 1:
            value = [value]
        from zeep.xsd.valueobjects import CompoundValue

        for item in value:

            # Find matching choice element
            for name, element in self.elements_nested:
                if isinstance(element, Element):
                    if element.name in item:
                        if isinstance(item, CompoundValue):
                            choice_value = getattr(item, element.name, item)
                        else:
                            choice_value = item.get(element.name)
                        element.render(parent, choice_value)
                        break
                else:
                    if name is not None:
                        if isinstance(item, CompoundValue):
                            choice_value = getattr(item, name, item)
                        else:
                            choice_value = item[name] if name in item else item
                    else:
                        choice_value = item

                    if element.accept(choice_value):
                        element.render(parent, choice_value)
                        break

    def signature(self):
        parts = []
        for name, element in self.elements_nested:
            if isinstance(element, Container):
                parts.append('{%s}' % (element.signature()))
            else:
                parts.append('{%s: %s}' % (name, element.signature()))
        part = '(%s)' % ' | '.join(parts)
        if self.max_occurs != 1:
            return '%s[]' % (part)
        return part


class Sequence(Container):

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

    def parse_xmlelements(self, xmlelements, schema, name=None):
        result = []
        for item in max_occurs_iter(self.max_occurs):
            item_result = {}
            for elm_name, element in self.elements:
                item_result[elm_name] = element.parse_xmlelements(
                    xmlelements, schema)
                if not xmlelements:
                    break
            result.append(item_result)

        if self.max_occurs == 1:
            return result[0] if result else None
        return {name: result}


class RefElement(object):

    def __init__(self, tag, ref, schema):
        self._ref = ref
        self._schema = schema

    def resolve(self):
        return self._schema.get_element(self._ref)


class RefAttribute(RefElement):

    def resolve(self):
        return self._schema.get_attribute(self._ref)
