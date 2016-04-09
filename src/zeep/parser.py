import os

from lxml import etree

from six.moves.urllib.parse import urljoin, urlparse


class ImportResolver(etree.Resolver):
    def __init__(self, transport, schema_references):
        self.schema_references = schema_references
        self.transport = transport

    def resolve(self, url, pubid, context):
        if url.startswith('intschema'):
            text = etree.tostring(self.schema_references[url])
            return self.resolve_string(text, context)

        if urlparse(url).scheme:
            content = self.transport.load(url)
            return self.resolve_string(content, context)


def parse_xml(content, transport, schema_references=None, base_url=None):
    parser = etree.XMLParser(remove_comments=True)
    parser.resolvers.add(ImportResolver(transport, schema_references))
    return etree.fromstring(content, parser=parser, base_url=base_url)


def load_external(url, transport, schema_references=None, base_url=None):
    if url.startswith('intschema'):
        assert schema_references
        return schema_references[url]

    if base_url:
        url = absolute_location(url, base_url)

    if urlparse(url).scheme:
        response = transport.load(url)
    else:
        with open(url, 'rb') as fh:
            response = fh.read()
    return parse_xml(response, transport, schema_references, base_url)


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
