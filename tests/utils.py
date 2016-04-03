from lxml import etree
from six import binary_type, string_types


def assert_nodes_equal(node_1, node_2):
    parser = etree.XMLParser(remove_blank_text=True)

    def _convert_node(node):
        if isinstance(node, (string_types, binary_type)):
            return etree.fromstring(node, parser=parser)
        return node

    text_1 = etree.tostring(_convert_node(node_1), pretty_print=True)
    text_2 = etree.tostring(_convert_node(node_2), pretty_print=True)
    assert text_1 == text_2
