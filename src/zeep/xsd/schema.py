import logging

from lxml import etree

from zeep.xsd import builtins as xsd_builtins
from zeep.xsd.visitor import SchemaVisitor

logger = logging.getLogger(__name__)


class Schema(object):

    def __init__(self, node=None, transport=None, references=None):
        self.transport = transport
        self.schema_references = references or {}
        self.xml_schema = None
        self._types = {}
        self.elements = {}
        self.target_namespace = None
        self.imports = {}
        self.element_form = 'unqualified'
        self.attribute_form = 'unqualified'

        if node is not None:
            if len(node) > 0:
                self.xml_schema = etree.XMLSchema(node)

            visitor = SchemaVisitor(schema=self)
            visitor.visit_schema(node)
            visitor.resolve()

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
