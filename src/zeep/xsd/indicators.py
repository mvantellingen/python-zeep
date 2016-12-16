from __future__ import print_function

import copy
import operator
from collections import OrderedDict, defaultdict, deque

from cached_property import threaded_cached_property

from zeep.exceptions import UnexpectedElementError
from zeep.xsd.elements import Any, Base, Element
from zeep.xsd.utils import (
    NamePrefixGenerator, UniqueNameGenerator, max_occurs_iter)

__all__ = ['All', 'Choice', 'Group', 'Sequence']


class Indicator(Base):

    def __repr__(self):
        return '<%s(%s)>' % (
            self.__class__.__name__, super(Indicator, self).__repr__())

    @threaded_cached_property
    def default_value(self):
        return OrderedDict([
            (name, element.default_value) for name, element in self.elements
        ])

    def clone(self, name, min_occurs=1, max_occurs=1):
        raise NotImplementedError()


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

    def clone(self, name, min_occurs=1, max_occurs=1):
        return self.__class__(
            elements=list(self),
            min_occurs=min_occurs,
            max_occurs=max_occurs)

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
        num = 0
        for name, element in self.elements_nested:
            if isinstance(element, Element):
                if element.name in values and values[element.name] is not None:
                    num += 1
            else:
                num += element.accept(values)
        return num

    def parse_args(self, args, index=0):
        result = {}
        for name, element in self.elements:
            if index >= len(args):
                break
            result[name] = args[index]
            index += 1

        return result, args, index

    def parse_kwargs(self, kwargs, name, available_kwargs):
        """Apply the given kwarg to the element.

        The available_kwargs is modified in-place. Returns a dict with the
        result.

        """
        if self.accepts_multiple:
            assert name

        if name and name in available_kwargs:

            # Make sure we have a list, lame lame
            item_kwargs = kwargs.get(name)
            if not isinstance(item_kwargs, list):
                item_kwargs = [item_kwargs]

            result = []
            for i, item_value in zip(max_occurs_iter(self.max_occurs), item_kwargs):
                item_kwargs = set(item_value.keys())
                subresult = OrderedDict()
                for item_name, element in self.elements:
                    value = element.parse_kwargs(item_value, item_name, item_kwargs)
                    if value is not None:
                        subresult.update(value)

                result.append(subresult)

            if self.accepts_multiple:
                result = {name: result}
            else:
                result = result[0] if result else None

            # All items consumed
            if not any(filter(None, item_kwargs)):
                available_kwargs.remove(name)

            return result

        else:
            result = OrderedDict()
            for elm_name, element in self.elements_nested:
                sub_result = element.parse_kwargs(kwargs, elm_name, available_kwargs)
                if sub_result:
                    result.update(sub_result)

            if name:
                result = {name: result}

            return result

    def resolve(self):
        for i, elm in enumerate(self):
            self[i] = elm.resolve()
        return self

    def render(self, parent, value):
        """Create subelements in the given parent object."""
        if not isinstance(value, list):
            values = [value]
        else:
            values = value

        for i, value in zip(max_occurs_iter(self.max_occurs), values):
            for name, element in self.elements_nested:
                if name:
                    if name in value:
                        element_value = value[name]
                    else:
                        element_value = None
                else:
                    element_value = value
                if element_value is not None or not element.is_optional:
                    element.render(parent, element_value)

    def signature(self, depth=()):
        """
        Use a tuple of element names as depth indicator, so that when an element is repeated,
        do not try to create its signature, as it would lead to infinite recursion
        """
        depth += (self.name,)
        parts = []
        for name, element in self.elements_nested:
            if hasattr(element, 'type') and element.type.name and element.type.name in depth:
                parts.append('{}: {}'.format(name, element.type.name))
            elif name:
                parts.append('%s: %s' % (name, element.signature(depth)))
            elif isinstance(element,  Indicator):
                parts.append('%s' % (element.signature(depth)))
            else:
                parts.append('%s: %s' % (name, element.signature(depth)))
        part = ', '.join(parts)

        if self.accepts_multiple:
            return '[%s]' % (part,)
        return part


class All(OrderIndicator):
    """Allows the elements in the group to appear (or not appear) in any order
    in the containing element.

    """

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        result = OrderedDict()
        expected_tags = {element.qname for __, element in self.elements}
        consumed_tags = set()

        values = defaultdict(deque)
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
        return OrderedDict()

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        """Return a dictionary"""
        result = []

        for i in max_occurs_iter(self.max_occurs):
            if not xmlelements:
                break

            for node in list(xmlelements):

                # Choose out of multiple
                options = []
                for element_name, element in self.elements_nested:

                    local_xmlelements = copy.copy(xmlelements)

                    try:
                        sub_result = element.parse_xmlelements(
                            local_xmlelements, schema, context=context)
                    except UnexpectedElementError:
                        continue

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
                        xmlelements.popleft()
                else:
                    break

        if self.accepts_multiple:
            result = {name: result}
        else:
            result = result[0] if result else {}
        return result

    def parse_kwargs(self, kwargs, name, available_kwargs):
        """Processes the kwargs for this choice element.

        Returns a dict containing the values found.

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
        if name and name in available_kwargs:
            values = kwargs[name] or []
            available_kwargs.remove(name)
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
                return {}

            result = {}

            # When choice elements are specified directly in the kwargs
            found = False
            for i, choice in enumerate(self):
                temp_kwargs = copy.copy(available_kwargs)
                subresult = choice.parse_kwargs(kwargs, None, temp_kwargs)

                if subresult:
                    if not any(subresult.values()):
                        available_kwargs.intersection_update(temp_kwargs)
                        result.update(subresult)
                    elif not found:
                        available_kwargs.intersection_update(temp_kwargs)
                        result.update(subresult)
                        found = True
            if found:
                for choice_name, choice in self.elements:
                    result.setdefault(choice_name, None)
            else:
                result = {}

        if name and self.accepts_multiple:
            result = {name: result}
        return result

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

    def accept(self, values):
        """Return the number of values which are accepted by this choice.

        If not all required elements are available then 0 is returned.

        """
        nums = set()
        for name, element in self.elements_nested:
            if isinstance(element, Element):
                if name in values and values[name]:
                    nums.add(1)
            else:
                num = element.accept(values)
                nums.add(num)
        return max(nums) if nums else 0

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

    def signature(self, depth=()):
        parts = []
        for name, element in self.elements_nested:
            if isinstance(element, OrderIndicator):
                parts.append('{%s}' % (element.signature(depth)))
            else:
                parts.append('{%s: %s}' % (name, element.signature(depth)))
        part = '(%s)' % ' | '.join(parts)
        if self.accepts_multiple:
            return '%s[]' % (part,)
        return part


class Sequence(OrderIndicator):

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        result = []
        for item in max_occurs_iter(self.max_occurs):
            if not xmlelements:
                break

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

    def clone(self, name, min_occurs=1, max_occurs=1):
        return self.__class__(
            name=self.qname,
            child=self.child,
            min_occurs=min_occurs,
            max_occurs=max_occurs)

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

    def parse_args(self, args, index=0):
        return self.child.parse_args(args, index)

    def parse_kwargs(self, kwargs, name, available_kwargs):
        if self.accepts_multiple:
            if name not in kwargs:
                return {}, kwargs

            available_kwargs.remove(name)
            item_kwargs = kwargs[name]

            result = []
            sub_name = '_value_1' if self.child.accepts_multiple else None
            for i, sub_kwargs in zip(max_occurs_iter(self.max_occurs), item_kwargs):
                available_sub_kwargs = set(sub_kwargs.keys())
                subresult = self.child.parse_kwargs(
                    sub_kwargs, sub_name, available_sub_kwargs)

                if subresult:
                    result.append(subresult)
            if result:
                result = {name: result}
        else:
            result = self.child.parse_kwargs(kwargs, name, available_kwargs)
        return result

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

    def signature(self, depth=()):
        return self.child.signature(depth)
