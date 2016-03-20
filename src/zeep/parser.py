from lxml import etree


class ImportResolver(etree.Resolver):
    def __init__(self, transport, schema_references):
        self.schema_references = schema_references
        self.transport = transport

    def resolve(self, url, pubid, context):
        if url.startswith('intschema'):
            text = etree.tostring(self.schema_references[url])
            return self.resolve_string(text, context)
        else:
            content = self.transport.load(url)
            return self.resolve_string(content, context)


def parse_xml(content, transport, schema_references=None):
    parser = etree.XMLParser(remove_comments=True)
    parser.resolvers.add(ImportResolver(transport, schema_references))
    return etree.fromstring(content, parser=parser)


def load_external(url, transport, schema_references=None):
    if url.startswith('intschema'):
        assert schema_references
        return schema_references[url]

    response = transport.load(url)
    return parse_xml(response, transport, schema_references)
