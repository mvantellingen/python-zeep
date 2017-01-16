class _SchemaRepository(object):
    """Mapping between schema target namespace and schema object"""
    def __init__(self):
        self._schemas = {}

    def add(self, schema):
        self._schemas[schema._target_namespace] = schema

    def get(self, namespace):
        if namespace in self._schemas:
            return self._schemas[namespace]

    def __contains__(self, namespace):
        return namespace in self._schemas

    def __len__(self):
        return len(self._schemas)


class ParserContext(object):
    """Parser context when parsing wsdl/xsd files"""
    def __init__(self):
        self.schema_objects = _SchemaRepository()

        # Mapping between internal nodes and original location
        self.schema_locations = {}


class XmlParserContext(object):
    """Parser context when parsing XML elements"""

    def __init__(self):
        self.schemas = []
