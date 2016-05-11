class SchemaRepository(object):
    def __init__(self):
        self._schemas = {}

    def add(self, schema):
        if schema._location:
            self._schemas[schema._location] = schema

    def get(self, location):
        if location in self._schemas:
            return self._schemas[location]

    def __len__(self):
        return len(self._schemas)


class SchemaNodeRepository(object):

    def __init__(self):
        self._nodes = {}

    def add(self, key, value):
        self._nodes[key] = value

    def get(self, key):
        return self._nodes[key]

    def __len__(self):
        return len(self._nodes)


class ParserContext(object):
    def __init__(self):
        self.schema_nodes = SchemaNodeRepository()
        self.schema_objects = SchemaRepository()
        self.schema_locations = {}
