from lxml import etree


def _soap_element(xmlelement, key):
    """So soap1.1 and 1.2 namespaces can be mixed HAH!"""
    namespaces = [
        'http://schemas.xmlsoap.org/wsdl/soap/',
        'http://schemas.xmlsoap.org/wsdl/soap12/',
    ]

    for ns in namespaces:
        retval = xmlelement.find('soap:%s' % key, namespaces={'soap': ns})
        if retval is not None:
            return retval


def etree_to_string(node):
    return etree.tostring(
        node, pretty_print=True, xml_declaration=True, encoding='utf-8')
