class SchemaRepository(object):
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


class SchemaNodeRepository(object):
    """Mapping between schema target namespace and lxml node"""
    def __init__(self):
        self._nodes = {}

    def add(self, key, value):
        self._nodes[key] = value

    def get(self, key):
        return self._nodes[key]

    def __len__(self):
        return len(self._nodes)


class ParserContext(object):
    """Parser context when parsing wsdl/xsd files"""
    def __init__(self):
        self.schema_nodes = SchemaNodeRepository()
        self.schema_objects = SchemaRepository()

        # Mapping between internal nodes and original location
        self.schema_locations = {}


class XmlParserContext(object):
    """Parser context when parsing XML elements"""

    def __init__(self):
        self.schemas = []
