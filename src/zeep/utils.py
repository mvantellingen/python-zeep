import pkg_resources
from lxml import etree


class _NotSetClass(object):
    def __repr__(self):
        return 'NotSet'


NotSet = _NotSetClass()


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


def get_version():
    return pkg_resources.require('zeep')[0].version
