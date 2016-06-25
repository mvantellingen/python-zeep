from defusedxml.lxml import fromstring
from lxml import etree

from six.moves.urllib.parse import urlparse
from zeep.exceptions import XMLSyntaxError
from zeep.parser import absolute_location


class ImportResolver(etree.Resolver):
    def __init__(self, transport, parser_context):
        self.parser_context = parser_context
        self.transport = transport

    def resolve(self, url, pubid, context):
        if url.startswith('intschema'):
            text = etree.tostring(self.parser_context.schema_nodes.get(url))
            return self.resolve_string(text, context)

        if urlparse(url).scheme in ('http', 'https'):
            content = self.transport.load(url)
            return self.resolve_string(content, context)


def parse_xml(content, transport, parser_context=None, base_url=None):
    parser = etree.XMLParser(remove_comments=True)
    parser.resolvers.add(ImportResolver(transport, parser_context))
    try:
        return fromstring(content, parser=parser, base_url=base_url)
    except etree.XMLSyntaxError as exc:
        raise XMLSyntaxError("Invalid XML content received (%s)" % exc.message)


def load_external(url, transport, parser_context=None, base_url=None):
    if url.startswith('intschema'):
        assert parser_context
        return parser_context.schema_nodes.get(url)

    if base_url:
        url = absolute_location(url, base_url)

    response = transport.load(url)
    return parse_xml(response, transport, parser_context, base_url)
