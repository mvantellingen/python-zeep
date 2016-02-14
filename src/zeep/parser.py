import requests
from lxml import etree


class ImportResolver(etree.Resolver):
    def __init__(self, schema_references):
        self.schema_references = schema_references

    def resolve(self, url, pubid, context):
        if url.startswith('intschema'):
            text = etree.tostring(self.schema_references[url])
            return self.resolve_string(text, context)
        else:
            print "LXML Resolving: ", url


def parse_xml(content, schema_references):
    parser = etree.XMLParser()
    parser.resolvers.add(ImportResolver(schema_references))
    return etree.fromstring(content, parser=parser)


def load_external(url, schema_references):
    response = requests.get(url)
    return parse_xml(response.content, schema_references)
