import copy

from lxml import etree


def process_multiref(node):
    """Iterate through the tree and replace the referened elements.

    This method replaces the nodes with an href attribute and replaces it
    with the elements it's referencing to (which have an id attribute).abs

    """
    multiref_objects = {
        elm.attrib['id']: elm for elm in node.xpath('//multiRef[@id]')
    }
    if not multiref_objects:
        return

    def fix_node_values(node, namespaces={}):
        # fix own attributes if prefix was lost
        for attr, val in node.items():
            if val.count(":") == 1:
                ns_components = val.split(":")
                if ns_components[0] not in namespaces:
                    # print "%s is no namespace prefix" % (ns_components[0])
                    continue
                if ns_components[0] not in node.nsmap.keys():
                    # print "lost namespace for %s, was: %s" % (ns_components[0], ns_uri)
                    ns_uri = namespaces.get(ns_components[0])
                    for prefix, namespace in node.nsmap.items():
                        if ns_uri == namespace:
                            # print "replaced with prefix %s for %s" % (prefix, namespace)
                            val = "%s:%s" % (prefix, "".join(ns_components[1:]))
                            node.set(attr, val)
        for child in node.iterchildren():
            fix_node_values(child, namespaces=namespaces)

    for id in multiref_objects:
        # TODO (In Soap 1.2 this is 'ref')
        reference = node.xpath('//*[@href=\'#%s\']' % id)[0]

        # get all namespaces used below this node for later fix
        all_namespaces = dict(multiref_objects[id].xpath("//namespace::*"))

        # Prepare replacement
        # nsmap is read-only on existing Elements, combine
        nsmap = dict(reference.nsmap)
        nsmap.update(multiref_objects[id].nsmap)
        attrib = dict(reference.attrib)
        attrib.update(multiref_objects[id].attrib)
        del attrib['href']

        # Create a copy with extended nsmap and move all children
        replacing_node = etree.Element(reference.tag, attrib=attrib, nsmap=nsmap)
        replacing_node.attrib.pop('id')
        replacing_node.text = multiref_objects[id].text
        replacing_node.extend(multiref_objects[id].getchildren())

        # Add replacing element and remove referring node and multiRef stub
        reference.addprevious(replacing_node)
        reference.getparent().remove(reference)
        multiref_objects[id].getparent().remove(multiref_objects[id])

        # The ElementTree modifications changed the nsmap for elements if the namespace was known in the parent.
        # But it does miss to also fit the attributes containing a prefix
        # Iterate the complete tree below the node and replace missing prefixes
        # Careful: That could lead to bugs if a prefix was used for different namespaces in separate multiRefs

        fix_node_values(replacing_node, all_namespaces)

    return
