from lxml import etree


def get_or_create_header(envelope):
    # find the namespace of the SOAP Envelope (because it's different for SOAP 1.1 and 1.2)
    root_tag = etree.QName(envelope)
    soap_envelope_namespace = root_tag.namespace
    # look for the Header element and create it if not found
    header_qname = '{%s}Header' % soap_envelope_namespace
    header = envelope.find(header_qname)
    if header is None:
        header = etree.Element(header_qname)
        envelope.insert(0, header)
    return header


def etree_to_string(node):
    return etree.tostring(
        node, pretty_print=True, xml_declaration=True, encoding='utf-8')
