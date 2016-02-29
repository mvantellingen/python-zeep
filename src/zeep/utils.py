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


def get_qname(node, name, target_namespace=None, as_text=True):
    value = node.get(name)
    if value is not None:
        qname = parse_qname(value, node.nsmap, target_namespace)
        if as_text:
            return qname.text
        return qname


def findall_multiple_ns(node, name, namespace_sets):
    result = []
    for nsmap in namespace_sets:
        result.extend(node.findall(name, namespaces=nsmap))
    return result
