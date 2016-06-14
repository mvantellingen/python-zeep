import copy
import pprint
from collections import OrderedDict

import six

from zeep.xsd.elements import Any, Choice, ListElement, Sequence

__all__ = ['AnyObject', 'CompoundValue']


class AnyObject(object):
    def __init__(self, xsd_type, value):
        self.xsd_type = xsd_type
        self.value = value

    def __repr__(self):
        return '<%s(type=%r, value=%r)>' % (
            self.__class__.__name__, self.xsd_type, self.value)


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

        items = _process_signature(fields, args, kwargs)
        fields = OrderedDict([(name, elm) for name, elm in fields])
        for key, value in items.items():

            if key in fields:
                field = fields[key]
                value = _convert_value(field, value)

            setattr(self, key, value)

    def __repr__(self):
        return pprint.pformat(self.__dict__, indent=4)


class ChoiceItem(object):
    def __init__(self, index, values):
        self.index = index
        self.values = values

    def __repr__(self):
        return '<%s(index=%r, values=%r)>' % (
            self.__class__.__name__, self.index, self.values)

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__ and
            self.__dict__ == other.__dict__)

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value


def _process_signature(fields, args, kwargs):
    """Return a dict with the args/kwargs mapped to the field name.

    Special handling is done for Choice elements since we need to record which
    element the user intends to use.

    :param fields: List of tuples (name, element)
    :type fields: list
    :param args: arg tuples
    :type args: tuple
    :param kwargs: kwargs
    :type kwargs: dict


    """
    result = {}

    all_fields = fields
    fields = list(fields)
    args = list(args)
    kwargs = copy.copy(kwargs)

    # Create a list of fields until field in any or choice

    num_pos_args = 0
    for name, element in fields:
        if element._require_keyword_arg:
            break
        num_pos_args += 1

    if len(args) > num_pos_args:
        raise TypeError(
            "__init__() takes at most %s positional arguments (%s given)" % (
                num_pos_args, len(args)))

    # Process the positional arguments
    for name, element in list(fields):
        if not args:
            break
        arg = args.pop(0)
        if element._require_keyword_arg:
            raise TypeError(
                "Any and Choice elements should be passed using a keyword argument")
        result[name] = arg
        fields.pop(0)
    if args:
        assert False

    # Process the keyword arguments
    for i, (name, element) in enumerate(fields):
        if isinstance(element, Choice):
            result[name] = _process_signature_choice(name, element, kwargs)

        elif name in kwargs:
            value = kwargs.pop(name)

            if isinstance(element, Any) and not isinstance(value, AnyObject):
                raise TypeError(
                    "%s: expected AnyObject, %s found" % (
                        name, type(value).__name__))

            result[name] = value

    if kwargs:
        raise TypeError(
            (
                "__init__() got an unexpected keyword argument %r, " +
                "Valid keyword arguments are: %s"
            ) % (next(six.iterkeys(kwargs)), ', '.join(x[0] for x in all_fields)))

    return result


def _process_signature_choice(name, element, kwargs):
    """Processes the kwargs for given choice element.

    Returns a list with multiple `utils.ChoiceItem` objects if maxOccurs > 1
    or simply one object if maxOccurs = 0.

    This handles two distinct initialization methods:

    1. Passing the choice elements directly to the kwargs (unnested)
    2. Passing the choice elements into the `name` kwarg (_choice_1) (nested).
       This case is required when multiple choice elements are given.

    :param name: Name of the choice element (_choice_1)
    :type name: str
    :param element: Choice element object
    :type element: zeep.xsd.Choice
    :param kwargs: dict (or list of dicts) of kwargs for initialization
    :type kwargs: list / dict

    """
    result = []
    if name in kwargs:
        values = kwargs.pop(name)
        if isinstance(values, dict):
            values = [values]

        for value in values:
            for choice_index, choice in enumerate(element.elements):

                if isinstance(choice, Sequence):
                    match = all(
                        child.name in value for child in choice
                        if not child.is_optional
                    )

                    if match:
                        result.append(ChoiceItem(choice_index, value))
                        break
                else:
                    if choice.name in value:
                        result.append(ChoiceItem(choice_index, value))
                        break
            else:
                raise TypeError(
                    "No complete xsd:Sequence found for the xsd:Choice %r.\n"
                    "The signature is: %s" % (name, element.signature(name)))

    else:

        # When choice elements are specified directly in the kwargs
        for choice_index, choice in enumerate(element.elements):

            if isinstance(choice, Sequence):
                match = all(
                    child.name in kwargs for child in choice
                    if not child.is_optional)

                if match:
                    item_values = {}
                    for child in choice:
                        if child.is_optional and child.name not in kwargs:
                            item_values[child.name] = None
                        else:
                            item_values[child.name] = kwargs.pop(child.name)
                    result.append(ChoiceItem(choice_index, item_values))
                    break
                elif any(
                    child.name in kwargs for child in choice
                    if not child.is_optional
                 ):
                    raise TypeError(
                        "No complete xsd:Choice %r.\n"
                        "The signature is: %s" % (name, element.signature(name)))

            else:
                if choice.name in kwargs:
                    result.append(
                        ChoiceItem(
                            choice_index,
                            {choice.name: kwargs.pop(choice.name)})
                    )

            if len(result) >= element.max_occurs:
                break

    if element.max_occurs == 1:
        if len(result) == 1:
            return result[0]
        elif len(result) > 1:
            raise TypeError("Number of items is larger then max_occurs")
        else:
            return ChoiceItem(0, {})
    return result


def _convert_value(field, value):

    if isinstance(field, Choice):
        return value

    if isinstance(value, dict):
        value = field(**value)

    elif isinstance(value, list):
        value = [_convert_value(field.type, v) for v in value]

    return value
