import os

from defusedxml.lxml import fromstring
from lxml import etree

from six.moves.urllib.parse import urljoin, urlparse


class ImportResolver(etree.Resolver):
    def __init__(self, transport, parser_context):
        self.parser_context = parser_context
        self.transport = transport

    def resolve(self, url, pubid, context):
        if url.startswith('intschema'):
            text = etree.tostring(self.parser_context.schema_nodes.get(url))
            return self.resolve_string(text, context)

        if urlparse(url).scheme:
            content = self.transport.load(url)
            return self.resolve_string(content, context)


def parse_xml(content, transport, parser_context=None, base_url=None):
    parser = etree.XMLParser(remove_comments=True)
    parser.resolvers.add(ImportResolver(transport, parser_context))
    return fromstring(content, parser=parser, base_url=base_url)


def load_external(url, transport, parser_context=None, base_url=None):
    if url.startswith('intschema'):
        assert parser_context
        return parser_context.schema_nodes.get(url)

    if base_url:
        url = absolute_location(url, base_url)

    if urlparse(url).scheme:
        response = transport.load(url)
    else:
        with open(url, 'rb') as fh:
            response = fh.read()
    return parse_xml(response, transport, parser_context, base_url)


def absolute_location(location, base):
    if location == base:
        return location

    if urlparse(location).scheme:
        return location

    if base and urlparse(base).scheme:
        return urljoin(base, location)
    else:
        if os.path.isabs(location):
            return location
        if base:
            return os.path.join(os.path.dirname(base), location)
    return location
