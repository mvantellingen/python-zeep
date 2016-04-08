import logging

from lxml import etree

from zeep.xsd import builtins as xsd_builtins
from zeep.xsd.visitor import SchemaVisitor

logger = logging.getLogger(__name__)


class SchemaRepository(object):
    def __init__(self):
        self._schema_by_location = {}

    def add(self, schema):
        if schema.location:
            self._schema_by_location[schema.location] = schema

    def get(self, location):
        if location in self._schema_by_location:
            return self._schema_by_location[location]


class Schema(object):

    def __init__(self, node=None, transport=None, references=None,
                 location=None, repository=None):
        self.location = location

        logger.debug("Init schema for %r", location)

        self.transport = transport
        self.schema_references = references or {}
        self.xml_schema = None
        self._types = {}
        self.elements = {}
        self.target_namespace = None
        self.imports = {}
        self.element_form = 'unqualified'
        self.attribute_form = 'unqualified'
        self.elm_instances = []

        if repository is None:
            self.repository = SchemaRepository()
        else:
            self.repository = repository
        self.repository.add(self)

        if node is not None:
            if len(node) > 0:
                self.xml_schema = etree.XMLSchema(node)

            visitor = SchemaVisitor(schema=self)
            visitor.visit_schema(node)

        if repository is None:
            for schema in self.imports.values():
                schema.resolve()
            self.resolve()

    def resolve(self):
        for type_ in self._types.values():
            type_.resolve(self)

        for element in self.elm_instances:
            element.resolve_type(self)
        self.elm_instances = []

    def register_type(self, name, value):
        assert not isinstance(value, type)

        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_type(%r, %r)", name, value)
        self._types[name] = value

    def register_element(self, name, value):
        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_element(%r, %r)", name, value)
        self.elements[name] = value

    def get_type(self, name):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        if name.text in xsd_builtins.default_types:
            return xsd_builtins.default_types[name]

        if name.text in self._types:
            return self._types[name]

        if name.namespace in self.imports:
            return self.imports[name.namespace].get_type(name)

        raise KeyError(
            "No such type: %r (Only have %s)" % (
                name.text, ', '.join(self._types)))

    @property
    def types(self):
        for value in self._types.values():
            yield value

        for schema in self.imports.values():
            for value in schema._types.values():
                yield value

    def get_element(self, name):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        if name in self.elements:
            return self.elements[name]

        if name.namespace in self.imports:
            return self.imports[name.namespace].get_element(name)

        raise KeyError(
            "No such element: %r (Only have %s)" % (
                name.text, ', '.join(self.elements)))

    def custom_type(self, name):
        return self.get_type(name)
