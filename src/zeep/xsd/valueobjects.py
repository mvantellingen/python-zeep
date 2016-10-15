import copy
from collections import OrderedDict

import six

from zeep.xsd.indicators import Indicator
from zeep.xsd.printer import PrettyPrinter

__all__ = ['AnyObject', 'CompoundValue']


class AnyObject(object):
    def __init__(self, xsd_element, value):
        self.xsd_elm = xsd_element
        self.value = value

    def __repr__(self):
        return '<%s(type=%r, value=%r)>' % (
            self.__class__.__name__, self.xsd_elm, self.value)

    def __deepcopy__(self, memo):
        return type(self)(self.xsd_elm, copy.deepcopy(self.value))


class CompoundValue(object):

    def __init__(self, *args, **kwargs):
        self.__values__ = OrderedDict()

        # Set default values
        for container_name, container in self._xsd_type.elements_nested:
            values = container.default_value
            if isinstance(container, Indicator):
                self.__values__.update(values)
            else:
                self.__values__[container_name] = values

        # Set attributes
        for attribute_name, attribute in self._xsd_type.attributes:
            self.__values__[attribute_name] = attribute.default_value

        # Set elements
        items = _process_signature(self._xsd_type, args, kwargs)
        for key, value in items.items():
            self.__values__[key] = value

    def __contains__(self, key):
        return self.__values__.__contains__(key)

    def __len__(self):
        return self.__values__.__len__()

    def __iter__(self):
        return self.__values__.__iter__()

    def __repr__(self):
        return PrettyPrinter().pformat(self.__values__)

    def __delitem__(self, key):
        return self.__values__.__delitem__(key)

    def __getitem__(self, key):
        return self.__values__[key]

    def __setitem__(self, key, value):
        self.__values__[key] = value

    def __setattr__(self, key, value):
        if key.startswith('__') or key in ('_xsd_type', '_xsd_elm'):
            return super(CompoundValue, self).__setattr__(key, value)
        self.__values__[key] = value

    def __getattribute__(self, key):
        if key.startswith('__') or key in ('_xsd_type', '_xsd_elm'):
            return super(CompoundValue, self).__getattribute__(key)
        try:
            return self.__values__[key]
        except KeyError:
            raise AttributeError(
                "%s instance has no attribute '%s'" % (
                    self.__class__.__name__, key))

    def __deepcopy__(self, memo):
        new = type(self)()
        new.__values__ = copy.deepcopy(self.__values__)
        for attr, value in self.__dict__.items():
            if attr != '__values__':
                setattr(new, attr, value)
        return new


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
    result = OrderedDict()
    args = list(args)
    num_args = len(args)

    # Since the args/kwargs are modified when processing we need to create a
    # copy first.
    args = copy.deepcopy(args)
    kwargs = copy.deepcopy(kwargs)


    # Process the positional arguments
    for element_name, element in xsd_type.elements_nested:
        values, args = element.parse_args(args)
        if not values:
            break
        result.update(values)

    if args:
        for attribute_name, attribute in xsd_type.attributes:
            result[attribute_name] = args.pop(0)

    if args:
        raise TypeError(
            "__init__() takes at most %s positional arguments (%s given)" % (
                len(result), num_args))

    # Process the named arguments (sequence/group/all/choice)
    for element_name, element in xsd_type.elements_nested:
        if element.accepts_multiple:
            values, kwargs = element.parse_kwargs(kwargs, element_name)
        else:
            values, kwargs = element.parse_kwargs(kwargs, None)

        if values is not None:
            for key, value in values.items():
                if key not in result:
                    result[key] = value

    # Process the named arguments for attributes
    for attribute_name, attribute in xsd_type.attributes:
        if attribute_name in kwargs:
            result[attribute_name] = kwargs.pop(attribute_name)

    if kwargs:
        raise TypeError((
            "%s() got an unexpected keyword argument %r. " +
            "Signature: (%s)"
        ) % (xsd_type.qname, next(six.iterkeys(kwargs)), xsd_type.signature()))

    return result
