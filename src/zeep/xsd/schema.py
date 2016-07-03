import logging
from collections import OrderedDict

from lxml import etree

from zeep import exceptions
from zeep.utils import NotSet
from zeep.xsd import builtins as xsd_builtins
from zeep.xsd.context import ParserContext
from zeep.xsd.visitor import SchemaVisitor

logger = logging.getLogger(__name__)


class Schema(object):
    """A schema is a collection of schema documents."""

    def __init__(self, node=None, transport=None, location=None,
                 parser_context=None):
        self._parser_context = parser_context or ParserContext()

        self._schemas = OrderedDict()
        self._root = None
        self._prefix_map = {}

        if node is not None:
            self._root = SchemaDocument(
                node, transport, location, self._parser_context, location)

            self._root.resolve()

            def _collect_imports_recursive(schema, target=None):
                if target is None:
                    target = OrderedDict()

                target[schema._target_namespace] = schema
                for ns, s in schema._imports.items():
                    if ns not in target:
                        _collect_imports_recursive(s, target)
                return target

            self._schemas = _collect_imports_recursive(self._root)
            self._prefix_map = self._create_prefix_map()

    def __repr__(self):
        return '<Schema(location=%r)>' % (self._root._location)

    @property
    def is_empty(self):
        return self._root.is_empty if self._root else True

    @property
    def elements(self):
        for schema in self._schemas.values():
            for element in schema._elements.values():
                yield element

    @property
    def types(self):
        for schema in self._schemas.values():
            for type_ in schema._types.values():
                yield type_

    def get_element(self, qname):
        qname = self._create_qname(qname)
        schema = self._get_schema_document(qname.namespace)
        try:
            return schema._elements[qname]
        except KeyError:
            known_elements = ', '.join(schema._elements.keys())
            raise KeyError(
                "No element '%s' in namespace %s. Available elements are: %s" % (
                    qname.localname, qname.namespace, known_elements or ' - '))

    def get_type(self, qname):
        qname = self._create_qname(qname)

        if qname.text in xsd_builtins.default_types:
            return xsd_builtins.default_types[qname]

        schema = self._get_schema_document(qname.namespace)
        try:
            return schema._types[qname]
        except KeyError:
            known_types = ', '.join(schema._types.keys())
            raise KeyError(
                "No type '%s' in namespace %s. Available types are: %s" % (
                    qname.localname, qname.namespace, known_types or ' - '))

    def _create_qname(self, name):
        if isinstance(name, etree.QName):
            return name

        if not name.startswith('{') and ':' in name and self._prefix_map:
            prefix, localname = name.split(':', 1)
            if prefix in self._prefix_map:
                return etree.QName(self._prefix_map[prefix], localname)
            else:
                raise ValueError(
                    "No namespace defined for the prefix %r" % prefix)
        else:
            return etree.QName(name)

    def _create_prefix_map(self):
        prefix_map = {}
        for i, namespace in enumerate(self._schemas.keys()):
            if namespace is None:
                continue
            prefix_map['ns%d' % i] = namespace
        return prefix_map

    def _get_schema_document(self, namespace):
        if namespace not in self._schemas:
            raise ValueError(
                "No schema available for the namespace %r" % namespace)
        return self._schemas[namespace]


class SchemaDocument(object):
    def __init__(self, node, transport, location, parser_context, base_url):
        logger.debug("Init schema for %r", location)
        assert node is not None
        assert parser_context

        # Internal
        self._base_url = base_url or location
        self._location = location
        self._transport = transport
        self._target_namespace = None
        self._elm_instances = []
        self._types = {}
        self._elements = {}
        self._attributes = {}
        self._imports = OrderedDict()
        self._element_form = 'unqualified'
        self._attribute_form = 'unqualified'
        self._resolved = False
        # self._xml_schema = None

        parser_context.schema_objects.add(self)

        if node is not None:
            # Disable XML schema validation for now
            # if len(node) > 0:
            #     self.xml_schema = etree.XMLSchema(node)

            visitor = SchemaVisitor(self, parser_context)
            visitor.visit_schema(node)

    def __repr__(self):
        return '<SchemaDocument(location=%r, tns=%r, is_empty=%r)>' % (
            self._location, self._target_namespace, self.is_empty)

    def resolve(self):
        logger.info("Resolving in schema %s", self)

        if self._resolved:
            return
        self._resolved = True

        for schema in self._imports.values():
            schema.resolve()

        for key, type_ in self._types.items():
            new = type_.resolve()
            assert new is not None, "resolve() should return a type"
            self._types[key] = new

        for element in self._elm_instances:
            element.resolve_type()
        self._elm_instances = []

    def register_type(self, name, value):
        assert not isinstance(value, type)
        assert value is not None

        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_type(%r, %r)", name, value)
        self._types[name] = value

    def register_element(self, name, value):
        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_element(%r, %r)", name, value)
        self._elements[name] = value

    def register_attribute(self, name, value):
        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_attribute(%r, %r)", name, value)
        self._attributes[name] = value

    def get_type(self, name, default=NotSet):
        name = self._create_qname(name)
        if name.text in xsd_builtins.default_types:
            return xsd_builtins.default_types[name]

        self._check_namespace_reference(name)
        if name.namespace == self._target_namespace:
            if name.text in self._types:
                return self._types[name]
            elif default is not NotSet:
                return default
            else:
                raise exceptions.XMLParseError(
                    "Unable to resolve type with QName '%s'" % name.text)
        else:
            if name.namespace in self._imports:
                return self._imports[name.namespace].get_type(name)
            else:
                raise exceptions.XMLParseError((
                    "Unable to resolve type with QName '%s' "
                    "(no schema imported with namespace '%s')"
                ) % (name.text, name.namespace))

    def get_element(self, name, default=NotSet):
        name = self._create_qname(name)
        self._check_namespace_reference(name)
        if name.namespace == self._target_namespace:
            if name.text in self._elements:
                return self._elements[name]
            elif default is not NotSet:
                return default
            else:
                raise exceptions.XMLParseError(
                    "Unable to resolve element with QName '%s'" % name.text)
        else:
            if name.namespace in self._imports:
                return self._imports[name.namespace].get_element(name)
            else:
                raise exceptions.XMLParseError((
                    "Unable to resolve element with QName '%s' " +
                    "(no schema imported with namespace '%s')"
                ) % (name.text, name.namespace))

        if default is not NotSet:
            return default

        raise exceptions.XMLParseError(
            "No such element: %r (Only have %s) (from: %s)" % (
                name.text, ', '.join(self._elements), self))

    def get_attribute(self, name, default=NotSet):
        name = self._create_qname(name)
        if name in self._attributes:
            return self._attributes[name]

        if name.namespace in self._imports:
            return self._imports[name.namespace].get_attribute(name)

        if default is not NotSet:
            return default

        raise exceptions.XMLParseError(
            "No such attribute: %r (Only have %s) (from: %s)" % (
                name.text, ', '.join(self._attributes), self))

    def _check_namespace_reference(self, name):
        """See https://www.w3.org/TR/xmlschema-1/#src-resolve"""
        ns = name.namespace

        if ns != self._target_namespace and ns not in self._imports.keys():
            raise exceptions.XMLParseError((
                "References from this schema (%r) to components in the " +
                "namespace '%s' are not allowed, since not indicated by an "
                "import statement."
            ) % (self._target_namespace, ns))

    def _create_qname(self, name):
        # TODO: Remove me
        if not isinstance(name, etree.QName):
            name = etree.QName(name)
        return name

    @property
    def is_empty(self):
        return not bool(self._imports or self._types or self._elements)
