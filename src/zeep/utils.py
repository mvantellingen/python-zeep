from lxml import etree


def parse_qname(value, nsmap, target_namespace=None):
    if value.startswith('{'):
        return etree.QName(value)

    if ':' in value:
        prefix, local = value.split(':')
        namespace = nsmap.get(prefix, prefix)
        return etree.QName(namespace, local)

    if target_namespace:
        return etree.QName(target_namespace, value)

    if None in nsmap:
        return etree.QName(nsmap[None], value)
    return etree.QName(value)


def get_qname(node, name, target_namespace=None):
    value = node.get(name)
    if value is not None:
        return parse_qname(value, node.nsmap, target_namespace).text
