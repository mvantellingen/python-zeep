import pprint
from collections import OrderedDict

import six

from zeep.xsd.elements import Choice, Container, Group

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
        for container_name, container in self._xsd_type.elements:
            if isinstance(container, Choice):
                continue

            if isinstance(container, (Container, Group)):
                for name, element in container.elements:

                    # XXX: element.default_value
                    if element.accepts_multiple:
                        value = []
                    else:
                        value = None
                    setattr(self, name, value)

            elif container.name:
                if container.accepts_multiple:
                    value = []
                else:
                    value = None
                setattr(self, container.name, value)

        items = _process_signature(self._xsd_type, args, kwargs)
        fields = OrderedDict([(name, elm) for name, elm in self._xsd_type.elements_all])
        for key, value in items.items():

            if key in fields:
                field = fields[key]
                value = _convert_value(field, value)

            setattr(self, key, value)

    def __contains__(self, key):
        return self.__dict__.__contains__(key)

    def __repr__(self):
        return pprint.pformat(self.__dict__, indent=4)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value


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
    for element_name, element in xsd_type.elements:
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
    for element_name, element in xsd_type.elements:
        if element.accepts_multiple:
            values, kwargs = element.parse_kwargs(kwargs, element_name)
        else:
            values, kwargs = element.parse_kwargs(kwargs, None)
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
            (
                "__init__() got an unexpected keyword argument %r. " +
                "Signature: (%s)"
            ) % (
                next(six.iterkeys(kwargs)), xsd_type.signature()
            ))
    return result


def _convert_value(field, value):

    if isinstance(field, Container):
        return value

    if isinstance(value, dict):
        value = field(**value)

    elif isinstance(value, list):
        value = [_convert_value(field.type, v) for v in value]

    return value
