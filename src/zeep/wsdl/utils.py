from lxml import etree


def get_or_create_header(envelope):
    header_qname = '{http://schemas.xmlsoap.org/soap/envelope/}Header'
    header = envelope.find(header_qname)
    if header is None:
        header = etree.Element(header_qname)
        envelope.insert(0, header)
    return header


def etree_to_string(node):
    return etree.tostring(
        node, pretty_print=True, xml_declaration=True, encoding='utf-8')
