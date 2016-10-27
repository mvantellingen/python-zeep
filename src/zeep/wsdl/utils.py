from lxml import etree

from zeep.utils import detect_soap_env


def get_or_create_header(envelope):
    soap_env = detect_soap_env(envelope)

    # look for the Header element and create it if not found
    header_qname = '{%s}Header' % soap_env
    header = envelope.find(header_qname)
    if header is None:
        header = etree.Element(header_qname)
        envelope.insert(0, header)
    return header


def etree_to_string(node):
    return etree.tostring(
        node, pretty_print=True, xml_declaration=True, encoding='utf-8')
