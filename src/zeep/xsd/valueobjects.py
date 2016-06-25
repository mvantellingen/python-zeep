import pprint
from collections import OrderedDict

import six

from zeep.xsd.elements import Container

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
        # Set default values
        for key, value in self._xsd_type.elements_all:
            if value.max_occurs != 1:
                value = []
            else:
                value = None
            setattr(self, key, value)

        items = _process_signature(self._xsd_type, args, kwargs)
        fields = OrderedDict([(name, elm) for name, elm in self._xsd_type.elements_all])
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


def _process_signature(xsd_type, args, kwargs):
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
    args = list(args)
    num_args = len(args)

    # Process the positional arguments
    for element in xsd_type.elements:
        values, args = element.parse_args(args)
        if not values:
            break
        result.update(values)

    if args:
        for attribute in xsd_type.attributes:
            result[attribute.name] = args.pop(0)

    if args:
        raise TypeError(
            "__init__() takes at most %s positional arguments (%s given)" % (
                len(result), num_args))

    # Process the named arguments (sequence/group/all/choice)
    for element in xsd_type.elements:
        values, kwargs = element.parse_kwargs(kwargs, None)
        if isinstance(values, ChoiceItem):
            values = values

        else:
            if values is not None:
                for key, value in values.items():
                    if key not in result:
                        result[key] = value

    # Process the named arguments for attributes
    for attribute in xsd_type.attributes:
        if attribute.name in kwargs:
            result[attribute.name] = kwargs.pop(attribute.name)

    if kwargs:
        raise TypeError(
            "__init__() got an unexpected keyword argument %r." % (
                next(six.iterkeys(kwargs))))

    return result


def _convert_value(field, value):

    if isinstance(field, Container):
        return value

    if isinstance(value, dict):
        value = field(**value)

    elif isinstance(value, list):
        value = [_convert_value(field.type, v) for v in value]

    return value
