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


def process_signature(attribute_order, args, kwargs):
    result = {}

    if len(args) > len(attribute_order):
        raise TypeError(
            '__init__() takes exactly %d arguments (%d given)' % (
                len(attribute_order), len(args)))

    for key, value in zip(attribute_order, args):
        if key in kwargs:
            raise TypeError(
                "__init__() got multiple values for keyword argument '%s'"
                % key)
        result[key] = value

    for key, value in kwargs.items():
        if key not in attribute_order:
            raise TypeError(
                "__init__() got an unexpected keyword argument %r" % key)
        result[key] = value

    return result
