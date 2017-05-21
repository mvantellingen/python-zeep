import copy

from lxml import etree


def process_multiref(node):
    """Iterate through the tree and replace the referened elements.

    This method replaces the nodes with an href attribute and replaces it
    with the elements it's referencing to (which have an id attribute).abs

    """
    multiref_objects = {
        elm.attrib['id']: elm for elm in node.xpath('*[@id]')
    }
    if not multiref_objects:
        return

    used_nodes = []

    def process(node):
        # TODO (In Soap 1.2 this is 'ref')
        href = node.attrib.get('href')

        if href and href.startswith('#'):
            obj = multiref_objects.get(href[1:])
            if obj is not None:
                used_nodes.append(obj)
                parent = node.getparent()

                new = _dereference_element(obj, node)

                # Replace the node with the new dereferenced node
                parent.insert(parent.index(node), new)
                parent.remove(node)
                node = new

        for child in node:
            process(child)

    process(node)

    # Remove the old dereferenced nodes from the tree
    for node in used_nodes:
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)


def _dereference_element(source, target):
    reverse_nsmap = {v: k for k, v in target.nsmap.items()}
    specific_nsmap = {k: v for k, v in source.nsmap.items() if k not in target.nsmap}

    new = etree.Element(target.tag, nsmap=specific_nsmap)

    # Copy the attributes. This is actually the difficult part since the
    # namespace prefixes can change in the attribute values. So for example
    # the xsi:type="ns11:my-type" need's to be parsed to use a new global
    # prefix.
    for key, value in source.attrib.items():
        if key == 'id':
            continue

        setted = False
        if value.count(':') == 1:
            prefix, localname = value.split(':')
            if prefix in specific_nsmap:
                namespace = specific_nsmap[prefix]
                if namespace in reverse_nsmap:
                    new.set(key, '%s:%s' % (reverse_nsmap[namespace], localname))
                    setted = True

        if not setted:
            new.set(key, value)

    # Copy the children and the text content
    for child in source:
        new.append(copy.deepcopy(child))
    new.text = source.text

    return new
