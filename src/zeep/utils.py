import copy

from lxml import etree


class _NotSetClass(object):
    def __repr__(self):
        return 'NotSet'


NotSet = _NotSetClass()


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


def qname_attr(node, attr_name, target_namespace=None):
    value = node.get(attr_name)
    if value is not None:
        return as_qname(value, node.nsmap, target_namespace)


def as_qname(value, nsmap, target_namespace):
    """Convert the given value to a QName"""
    if ':' in value:
        prefix, local = value.split(':')
        namespace = nsmap.get(prefix, prefix)
        return etree.QName(namespace, local)

    if target_namespace:
        return etree.QName(target_namespace, value)

    if None in nsmap:
        return etree.QName(nsmap[None], value)
    return etree.QName(value)


def findall_multiple_ns(node, name, namespace_sets):
    result = []
    for nsmap in namespace_sets:
        result.extend(node.findall(name, namespaces=nsmap))
    return result


def process_signature(fields, args, kwargs):
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

    fields = list(fields)
    args = list(args)
    kwargs = copy.copy(kwargs)

    # Create a list of fields until field in any or choice
    from zeep.xsd import AnyObject, Choice, Any

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
            result[name] = process_signature_choice(name, element, kwargs)

        elif name in kwargs:
            value = kwargs[name]

            if isinstance(element, Any) and not isinstance(value, AnyObject):
                raise TypeError(
                    "%s: expected AnyObject, %s found" % (
                        name, type(value).__name__))

            result[name] = value
    return result


def process_signature_choice(name, element, kwargs):
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
    from zeep.xsd import Sequence

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
            return ChoiceItem(0, [])
    return result
