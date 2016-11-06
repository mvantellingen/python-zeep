import inspect


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

    if nsmap.get(None):
        return etree.QName(nsmap[None], value)
    return etree.QName(value)


def findall_multiple_ns(node, name, namespace_sets):
    result = []
    for nsmap in namespace_sets:
        result.extend(node.findall(name, namespaces=nsmap))
    return result


def get_version():
    from zeep import __version__  # cyclic import

    return __version__


def get_base_class(objects):
    """Return the best base class for multiple objects.

    Implementation is quick and dirty, might be done better.. ;-)

    """
    bases = [inspect.getmro(obj.__class__)[::-1] for obj in objects]
    num_objects = len(objects)
    max_mro = max(len(mro) for mro in bases)

    base_class = None
    for i in range(max_mro):
        try:
            if len({bases[j][i] for j in range(num_objects)}) > 1:
                break
        except IndexError:
            break
        base_class = bases[0][i]
    return base_class
