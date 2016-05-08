from lxml import etree
from six import binary_type, string_types, text_type


def load_xml(xml):
    parser = etree.XMLParser(remove_blank_text=True)
    return etree.fromstring(xml.strip(), parser=parser)


def assert_nodes_equal(node_1, node_2):
    def _convert_node(node):
        if isinstance(node, (string_types, binary_type)):
            return load_xml(node)
        return node

    text_1 = etree.tostring(_convert_node(node_1), pretty_print=True)
    text_2 = etree.tostring(_convert_node(node_2), pretty_print=True)
    assert text_type(text_1) == text_type(text_2)
