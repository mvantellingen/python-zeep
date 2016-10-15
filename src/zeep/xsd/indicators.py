from __future__ import print_function

import copy
import operator
from collections import OrderedDict, defaultdict

from cached_property import threaded_cached_property

from zeep.xsd.elements import Any, Base, Element
from zeep.xsd.utils import (
    NamePrefixGenerator, UniqueNameGenerator, max_occurs_iter)

__all__ = ['All', 'Choice', 'Group', 'Sequence']


class Indicator(Base):

    def __repr__(self):
        return '<%s(%s)>' % (
            self.__class__.__name__, super(Indicator, self).__repr__())

    @property
    def default_value(self):
        result = OrderedDict()
        for name, element in self.elements:
            result[name] = element.default_value
        return result

    def clone(self, name, min_occurs=1, max_occurs=1):
        new = copy.copy(self)
        new.min_occurs = min_occurs
        new.max_occurs = max_occurs
        return new


class OrderIndicator(Indicator, list):
    name = None

    def __init__(self, elements=None, min_occurs=1, max_occurs=1):
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs

        if elements is None:
            super(OrderIndicator, self).__init__()
        else:
            super(OrderIndicator, self).__init__()
            self.extend(elements)

    @threaded_cached_property
    def elements(self):
        """List of tuples containing the element name and the element"""
        result = []
        for name, elm in self.elements_nested:
            if name is None:
                result.extend(elm.elements)
            else:
                result.append((name, elm))
        return result

    @threaded_cached_property
    def elements_nested(self):
        """List of tuples containing the element name and the element"""
        result = []
        generator = NamePrefixGenerator()
        generator_2 = UniqueNameGenerator()

        for elm in self:
            if isinstance(elm, (All, Choice, Group, Sequence)):
                if elm.accepts_multiple:
                    result.append((generator.get_name(), elm))
                else:
                    for sub_name, sub_elm in elm.elements:
                        sub_name = generator_2.create_name(sub_name)
                    result.append((None, elm))
            elif isinstance(elm, (Any, Choice)):
                result.append((generator.get_name(), elm))
            else:
                name = generator_2.create_name(elm.attr_name)
                result.append((name, elm))
        return result

    def accept(self, values):
        """Return the number of values which are accepted by this choice.

        If not all required elements are available then 0 is returned.

        """
        values = {k for k in values if values[k] is not None}

        required_keys = {
            name for name, element in self.elements_nested
            if not element.is_optional
        }
        optional_keys = {
            name for name, element in self.elements
            if element.is_optional
        }

        values_keys = set(values)

        if (required_keys <= values_keys):
            return len(values_keys & (required_keys | optional_keys))
        return 0

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
                subresult = OrderedDict()
                for item_name, element in self.elements:
                    value, item_value = element.parse_kwargs(item_value, item_name)
                    if value is not None:
                        subresult.update(value)

                result.append(subresult)

            if self.accepts_multiple:
                result = {name: result}
            else:
                result = result[0] if result else None

            # All items consumed
            if not any(filter(None, item_kwargs)):
                del kwargs[name]

            return result, kwargs

        else:
            result = OrderedDict()
            for elm_name, element in self.elements:
                sub_result, kwargs = element.parse_kwargs(kwargs, elm_name)
                if sub_result is not None:
                    result.update(sub_result)

            if name:
                result = {name: result}

            return result, kwargs

    def resolve(self):
        for i, elm in enumerate(self):
            self[i] = elm.resolve()
        return self

    def render(self, parent, value):
        """Create subelements in the given parent object.

        To make sure we render values only once the value items are copied
        and the rendered attribute is removed from it once it is rendered.

        """
        if not isinstance(value, list):
            values = [value]
        else:
            values = value

        for i, value in zip(max_occurs_iter(self.max_occurs), values):
            value = copy.copy(value)

            for name, element in self.elements_nested:
                if name:
                    if name in value:
                        element_value = value[name]
                        del value[name]
                    else:
                        element_value = None
                else:
                    element_value = value
                if element_value is not None or not element.is_optional:
                    element.render(parent, element_value)

    def signature(self, depth=0):
        depth += 1
        parts = []
        for name, element in self.elements_nested:
            if name:
                parts.append('%s: %s' % (name, element.signature(depth)))
            elif isinstance(element,  Indicator):
                parts.append('%s' % (element.signature(depth)))
            else:
                parts.append('%s: %s' % (name, element.signature(depth)))
        part = ', '.join(parts)

        if self.accepts_multiple:
            return '[%s]' % (part)
        return part


class All(OrderIndicator):
    """Allows the elements in the group to appear (or not appear) in any order
    in the containing element.

    """

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        result = OrderedDict()
        expected_tags = {element.qname for __, element in self.elements}
        consumed_tags = set()

        values = defaultdict(list)
        for i, elm in enumerate(xmlelements):
            if elm.tag in expected_tags:
                consumed_tags.add(i)
                values[elm.tag].append(elm)

        # Remove the consumed tags from the xmlelements
        for i in sorted(consumed_tags, reverse=True):
            del xmlelements[i]

        for name, element in self.elements:
            sub_elements = values.get(element.qname)
            if sub_elements:
                result[name] = element.parse_xmlelements(
                    sub_elements, schema, context=context)

        return result


class Choice(OrderIndicator):

    @property
    def is_optional(self):
        return True

    @property
    def default_value(self):
        return {}

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        """Return a dictionary"""
        result = []

        for i in max_occurs_iter(self.max_occurs):
            if len(xmlelements) < 1:
                break
            for node in list(xmlelements):

                # Choose out of multiple
                options = []
                for element_name, element in self.elements_nested:

                    local_xmlelements = copy.copy(xmlelements)
                    sub_result = element.parse_xmlelements(
                        local_xmlelements, schema, context=context)

                    if isinstance(element, OrderIndicator):
                        if element.accepts_multiple:
                            sub_result = {element_name: sub_result}
                    else:
                        sub_result = {element_name: sub_result}

                    num_consumed = len(xmlelements) - len(local_xmlelements)
                    if num_consumed:
                        options.append((num_consumed, sub_result))

                if not options:
                    xmlelements = []
                    break

                # Sort on least left
                options = sorted(options, key=operator.itemgetter(0), reverse=True)
                if options:
                    result.append(options[0][1])
                    for i in range(options[0][0]):
                        xmlelements.pop(0)
                else:
                    break

        if self.accepts_multiple:
            result = {name: result}
        else:
            result = result[0] if result else {}
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
        kwargs = copy.copy(kwargs)
        if name and name in kwargs:
            values = kwargs.pop(name) or []
            result = []

            if isinstance(values, dict):
                values = [values]

            for value in values:
                for element in self:
                    # TODO: Use most greedy choice instead of first matching
                    if isinstance(element, OrderIndicator):
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

            result = {}
            for choice_name, choice in self.elements:
                result[choice_name] = None

            # When choice elements are specified directly in the kwargs
            org_kwargs = kwargs
            for choice in self:
                subresult, kwargs = choice.parse_kwargs(org_kwargs)
                if subresult:
                    result.update(subresult)
                    break
            else:
                result = {}
                kwargs = org_kwargs

        if name and self.accepts_multiple:
            result = {name: result}
        return result, kwargs

    def render(self, parent, value):
        """Render the value to the parent element tree node.

        This is a bit more complex then the order render methods since we need
        to search for the best matching choice element.

        """
        if not self.accepts_multiple:
            value = [value]

        for item in value:
            result = self._find_element_to_render(item)
            if result:
                element, choice_value = result
                element.render(parent, choice_value)

    def _find_element_to_render(self, value):
        """Return a tuple (element, value) for the best matching choice"""
        matches = []

        for name, element in self.elements_nested:
            if isinstance(element, Element):
                if element.name in value:
                    try:
                        choice_value = value[element.name]
                    except KeyError:
                        choice_value = value

                    if choice_value is not None:
                        matches.append((1, element, choice_value))
            else:
                if name is not None:
                    try:
                        choice_value = value[name]
                    except KeyError:
                        choice_value = value
                else:
                    choice_value = value

                score = element.accept(choice_value)
                if score:
                    matches.append((score, element, choice_value))

        if matches:
            matches = sorted(matches, key=operator.itemgetter(0), reverse=True)
            return matches[0][1:]

    def signature(self, depth=0):
        parts = []
        for name, element in self.elements_nested:
            if isinstance(element, OrderIndicator):
                parts.append('{%s}' % (element.signature(depth)))
            else:
                parts.append('{%s: %s}' % (name, element.signature(depth)))
        part = '(%s)' % ' | '.join(parts)
        if self.accepts_multiple:
            return '%s[]' % (part)
        return part


class Sequence(OrderIndicator):

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        result = []
        for item in max_occurs_iter(self.max_occurs):
            item_result = OrderedDict()
            for elm_name, element in self.elements:
                item_subresult = element.parse_xmlelements(
                    xmlelements, schema, name, context=context)

                # Unwrap if allowed
                if isinstance(element, OrderIndicator):
                    item_result.update(item_subresult)
                else:
                    item_result[elm_name] = item_subresult

                if not xmlelements:
                    break
            if item_result:
                result.append(item_result)

        if not self.accepts_multiple:
            return result[0] if result else None

        return {name: result}


class Group(Indicator):
    """Groups a set of element declarations so that they can be incorporated as
    a group into complex type definitions.

    """

    def __init__(self, name, child, max_occurs=1, min_occurs=1):
        super(Group, self).__init__()
        self.child = child
        self.qname = name
        self.name = name.localname
        self.max_occurs = max_occurs
        self.min_occurs = min_occurs

    def __str__(self):
        return '%s(%s)' % (self.name, self.signature())

    def __iter__(self, *args, **kwargs):
        for item in self.child:
            yield item

    @threaded_cached_property
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

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        result = []

        for i in max_occurs_iter(self.max_occurs):
            result.append(
                self.child.parse_xmlelements(
                    xmlelements, schema, name, context=context)
            )
        if not self.accepts_multiple and result:
            return result[0]
        return {name: result}

    def render(self, *args, **kwargs):
        return self.child.render(*args, **kwargs)

    def resolve(self):
        self.child = self.child.resolve()
        return self

    def signature(self, depth=0):
        return self.child.signature(depth)
