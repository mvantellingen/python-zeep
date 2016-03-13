import requests
from lxml import etree


class ImportResolver(etree.Resolver):
    def __init__(self, schema_references, transport):
        self.schema_references = schema_references
        self.transport = transport
        assert self.transport

    def resolve(self, url, pubid, context):
        if url.startswith('intschema'):
            text = etree.tostring(self.schema_references[url])
            return self.resolve_string(text, context)
        else:
            content = self.transport.load(url)
            return self.resolve_string(content, context)


def parse_xml(content, schema_references, transport):
    parser = etree.XMLParser(remove_comments=True)
    parser.resolvers.add(ImportResolver(schema_references, transport))
    return etree.fromstring(content, parser=parser)


def load_external(url, schema_references, transport):
    response = requests.get(url)
    return parse_xml(response.content, schema_references, transport)
