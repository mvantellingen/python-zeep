import logging

from lxml import etree

from zeep.xsd import builtins as xsd_builtins
from zeep.xsd.context import ParserContext
from zeep.xsd.visitor import SchemaVisitor

logger = logging.getLogger(__name__)


class Schema(object):

    def __init__(self, node=None, transport=None, location=None,
                 parser_context=None):
        logger.debug("Init schema for %r", location)

        # Internal
        self._location = location
        self._transport = transport
        self._target_namespace = None
        self._elm_instances = []
        self._types = {}
        self._elements = {}
        self._imports = {}
        self._xml_schema = None
        self._element_form = 'unqualified'
        self._attribute_form = 'unqualified'

        is_root_schema = False
        if not parser_context:
            parser_context = ParserContext()
        if not parser_context.schema_objects:
            is_root_schema = True
        parser_context.schema_objects.add(self)

        if node is not None:
            # Disable XML schema validation for now
            # if len(node) > 0:
            #     self.xml_schema = etree.XMLSchema(node)

            visitor = SchemaVisitor(self, parser_context)
            visitor.visit_schema(node)

        if is_root_schema:
            for schema in self._imports.values():
                schema.resolve()
            self.resolve()

    def __repr__(self):
        return '<Schema(location=%r)>' % (self._location)

    def resolve(self):
        for type_ in self._types.values():
            type_.resolve(self)

        for element in self._elm_instances:
            element.resolve_type(self)
        self._elm_instances = []

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
        self._elements[name] = value

    def get_type(self, name):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        if name.text in xsd_builtins.default_types:
            return xsd_builtins.default_types[name]

        if name.text in self._types:
            return self._types[name]

        if name.namespace in self._imports:
            return self._imports[name.namespace].get_type(name)

        raise KeyError(
            "No such type: %r (Only have %s)" % (
                name.text, ', '.join(self._types)))

    @property
    def types(self):
        for value in self._types.values():
            yield value

        for schema in self._imports.values():
            for value in schema._types.values():
                yield value

    def get_element(self, name):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        if name in self._elements:
            return self._elements[name]

        if name.namespace in self._imports:
            return self._imports[name.namespace].get_element(name)

        raise KeyError(
            "No such element: %r (Only have %s) (from: %s)" % (
                name.text, ', '.join(self._elements), self))

    def custom_type(self, name):
        return self.get_type(name)
