from collections import OrderedDict, defaultdict

from lxml import etree


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
    result = {}
    field_map = OrderedDict([
        (name, (elm, container)) for name, elm, container in fields
    ])

    # XXX len(args) > len(attribute_order - num choice elms)
    if len(args) > len(fields):
        raise TypeError(
            '__init__() takes exactly %d arguments (%d given)' % (
                len(fields), len(args)))

    # Ignore choices
    for key, value in zip(field_map.keys(), args):
        if key in kwargs:
            raise TypeError(
                "__init__() got multiple values for keyword argument '%s'"
                % key)

        element, container = field_map[key]
        if container:
            raise TypeError(
                "Choice element value (%s) can only be set via " +
                "named arguments" % (key))

        result[key] = value

    element_counts = defaultdict(lambda: 0)
    for key, value in kwargs.items():
        if key not in field_map:
            raise TypeError(
                "__init__() got an unexpected keyword argument %r" % key)
        element, container = field_map[key]
        count_key = container.key if container else key

        if isinstance(value, list):
            element_counts[count_key] += len(value)
        else:
            element_counts[count_key] += 1
        num_items = element_counts[count_key]

        if container:
            if container.max_occurs and num_items > container.max_occurs:
                raise ValueError(
                    "%s item can occur at max %d times, received: %d" % (
                        container.__class__.__name__,
                        container.max_occurs, num_items))

        else:
            if element.max_occurs and num_items > element.max_occurs:
                raise ValueError(
                    "%s element can occur at max %d times, received: %d" % (
                        key, element.max_occurs, num_items))

        result[key] = value

    return result
