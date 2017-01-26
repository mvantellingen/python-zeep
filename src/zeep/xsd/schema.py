import logging
from collections import OrderedDict

from lxml import etree

from zeep import exceptions
from zeep.xsd import const
from zeep.xsd.elements import builtins as xsd_builtins_elements
from zeep.xsd.types import builtins as xsd_builtins_types
from zeep.xsd.visitor import SchemaVisitor

logger = logging.getLogger(__name__)


class Schema(object):
    """A schema is a collection of schema documents."""

    def __init__(self, node=None, transport=None, location=None):
        self._transport = transport

        self._documents = OrderedDict()
        self._prefix_map_auto = {}
        self._prefix_map_custom = {}

        if not isinstance(node, list):
            nodes = [node] if node is not None else []
        else:
            nodes = node
        self.add_documents(nodes, location)

    @property
    def documents(self):
        for documents in self._documents.values():
            for document in documents:
                yield document

    @property
    def prefix_map(self):
        retval = {}
        retval.update(self._prefix_map_custom)
        retval.update({
            k: v for k, v in self._prefix_map_auto.items()
            if v not in retval.values()
        })
        return retval

    @property
    def is_empty(self):
        """Boolean to indicate if this schema contains any types or elements"""
        return all(document.is_empty for document in self.documents)

    @property
    def namespaces(self):
        return set(self._documents.keys())

    @property
    def elements(self):
        """Yield all globla xsd.Type objects"""
        for document in self.documents:
            for element in document._elements.values():
                yield element

    @property
    def types(self):
        """Yield all globla xsd.Type objects"""
        for document in self.documents:
            for type_ in document._types.values():
                yield type_

    def __repr__(self):
        if self._documents:
            main_doc = next(self.documents)
            location = main_doc._location
        else:
            location = '<none>'
        return '<Schema(location=%r)>' % location

    def add_documents(self, schema_nodes, location):
        documents = []
        for node in schema_nodes:
            document = self.create_new_document(node, location)
            documents.append(document)

        for document in documents:
            document.resolve()

        self._prefix_map_auto = self._create_prefix_map()

    def get_element(self, qname):
        """Return a global xsd.Element object with the given qname"""
        qname = self._create_qname(qname)
        if qname.text in xsd_builtins_elements.default_elements:
            return xsd_builtins_elements.default_elements[qname]

        # Handle XSD namespace items
        if qname.namespace == const.NS_XSD:
            try:
                return xsd_builtins_elements.default_elements[qname]
            except KeyError:
                raise exceptions.LookupError("No such type %r" % qname.text)

        return self._get_instance(qname, 'get_element', 'element')

    def get_type(self, qname, fail_silently=False):
        """Return a global xsd.Type object with the given qname"""
        qname = self._create_qname(qname)

        # Handle XSD namespace items
        if qname.namespace == const.NS_XSD:
            try:
                return xsd_builtins_types.default_types[qname]
            except KeyError:
                raise exceptions.LookupError("No such type %r" % qname.text)

        try:
            return self._get_instance(qname, 'get_type', 'type')
        except exceptions.NamespaceError as exc:
            if fail_silently:
                logger.info(str(exc))
            else:
                raise

    def get_group(self, qname):
        """Return a global xsd.Group object with the given qname"""
        return self._get_instance(qname, 'get_group', 'group')

    def get_attribute(self, qname):
        """Return a global xsd.attributeGroup object with the given qname"""
        return self._get_instance(qname, 'get_attribute', 'attribute')

    def get_attribute_group(self, qname):
        """Return a global xsd.attributeGroup object with the given qname"""
        return self._get_instance(qname, 'get_attribute_group', 'attributeGroup')

    def set_ns_prefix(self, prefix, namespace):
        self._prefix_map_custom[prefix] = namespace

    def get_ns_prefix(self, prefix):
        try:
            try:
                return self._prefix_map_custom[prefix]
            except KeyError:
                return self._prefix_map_auto[prefix]
        except KeyError:
            raise ValueError("No such prefix %r" % prefix)

    def create_new_document(self, node, url, base_url=None):
        namespace = node.get('targetNamespace') if node is not None else None
        if base_url is None:
            base_url = url

        schema = SchemaDocument(namespace, url, base_url)
        self._add_schema_document(schema)
        schema.load(self, node)
        return schema

    def merge(self, schema):
        """Merge an other XSD schema in this one"""
        for document in schema.documents:
            self._add_schema_document(document)
        self._prefix_map_auto = self._create_prefix_map()

    def _get_instance(self, qname, method_name, name):
        """Return an object from one of the SchemaDocument's"""
        qname = self._create_qname(qname)
        try:
            last_exception = None
            for schema in self._get_schema_documents(qname.namespace):
                method = getattr(schema, method_name)
                try:
                    return method(qname)
                except exceptions.LookupError as exc:
                    last_exception = exc
                    continue
            raise last_exception

        except exceptions.NamespaceError:
            raise exceptions.NamespaceError((
                "Unable to resolve %s %s. " +
                "No schema available for the namespace %r."
            ) % (name, qname.text, qname.namespace))

    def _create_qname(self, name):
        """Create an `lxml.etree.QName()` object for the given qname string.

        This also expands the shorthand notation.

        """
        if isinstance(name, etree.QName):
            return name

        if not name.startswith('{') and ':' in name and self._prefix_map_auto:
            prefix, localname = name.split(':', 1)
            if prefix in self._prefix_map_custom:
                return etree.QName(self._prefix_map_custom[prefix], localname)
            elif prefix in self._prefix_map_auto:
                return etree.QName(self._prefix_map_auto[prefix], localname)
            else:
                raise ValueError(
                    "No namespace defined for the prefix %r" % prefix)
        else:
            return etree.QName(name)

    def _create_prefix_map(self):
        prefix_map = {
            'xsd': 'http://www.w3.org/2001/XMLSchema',
        }
        for i, namespace in enumerate(self._documents.keys()):
            if namespace is None:
                continue
            prefix_map['ns%d' % i] = namespace
        return prefix_map

    def _has_schema_document(self, namespace):
        return namespace in self._documents

    def _add_schema_document(self, document):
        logger.info("Add document with tns %s to schema %s", document.namespace, id(self))
        documents = self._documents.setdefault(document.namespace, [])
        documents.append(document)

    def _get_schema_document(self, namespace, location):
        for document in self._documents.get(namespace, []):
            if document._location == location:
                return document

    def _get_schema_documents(self, namespace, fail_silently=False):
        if namespace not in self._documents:
            if fail_silently:
                return []
            raise exceptions.NamespaceError(
                "No schema available for the namespace %r" % namespace)
        return self._documents[namespace]


class SchemaDocument(object):
    def __init__(self, namespace, location, base_url):
        logger.debug("Init schema document for %r", location)

        # Internal
        self._base_url = base_url or location
        self._location = location
        self._target_namespace = namespace
        self._elm_instances = []

        self._attribute_groups = {}
        self._attributes = {}
        self._elements = {}
        self._groups = {}
        self._types = {}

        self._imports = OrderedDict()
        self._element_form = 'unqualified'
        self._attribute_form = 'unqualified'
        self._resolved = False
        # self._xml_schema = None

    def __repr__(self):
        return '<SchemaDocument(location=%r, tns=%r, is_empty=%r)>' % (
            self._location, self._target_namespace, self.is_empty)

    @property
    def namespace(self):
        return self._target_namespace

    @property
    def is_empty(self):
        return not bool(self._imports or self._types or self._elements)

    def load(self, schema, node):
        if node is None:
            return

        if not schema._has_schema_document(self._target_namespace):
            raise RuntimeError(
                "The document needs to be registered in the schema before " +
                "it can be loaded")

        # Disable XML schema validation for now
        # if len(node) > 0:
        #     self.xml_schema = etree.XMLSchema(node)
        visitor = SchemaVisitor(schema, self)
        visitor.visit_schema(node)

    def resolve(self):
        logger.info("Resolving in schema %s", self)

        if self._resolved:
            return
        self._resolved = True

        for schemas in self._imports.values():
            for schema in schemas:
                schema.resolve()

        def _resolve_dict(val):
            for key, obj in val.items():
                new = obj.resolve()
                assert new is not None, "resolve() should return an object"
                val[key] = new

        _resolve_dict(self._attribute_groups)
        _resolve_dict(self._attributes)
        _resolve_dict(self._elements)
        _resolve_dict(self._groups)
        _resolve_dict(self._types)

        for element in self._elm_instances:
            element.resolve()
        self._elm_instances = []

    def register_import(self, namespace, schema):
        schemas = self._imports.setdefault(namespace, [])
        schemas.append(schema)

    def is_imported(self, namespace):
        return namespace in self._imports

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

    def register_group(self, name, value):
        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_group(%r, %r)", name, value)
        self._groups[name] = value

    def register_attribute(self, name, value):
        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_attribute(%r, %r)", name, value)
        self._attributes[name] = value

    def register_attribute_group(self, name, value):
        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_attribute_group(%r, %r)", name, value)
        self._attribute_groups[name] = value

    def get_type(self, qname):
        """Return a xsd.Type object from this schema"""
        return self._get_instance(qname, self._types, 'type')

    def get_element(self, qname):
        """Return a xsd.Element object from this schema"""
        return self._get_instance(qname, self._elements, 'element')

    def get_group(self, qname):
        """Return a xsd.Group object from this schema"""
        return self._get_instance(qname, self._groups, 'group')

    def get_attribute(self, qname):
        """Return a xsd.Attribute object from this schema"""
        return self._get_instance(qname, self._attributes, 'attribute')

    def get_attribute_group(self, qname):
        """Return a xsd.AttributeGroup object from this schema"""
        return self._get_instance(qname, self._attribute_groups, 'attributeGroup')

    def _get_instance(self, qname, items, item_name):
        try:
            return items[qname]
        except KeyError:
            known_items = ', '.join(items.keys())
            raise exceptions.LookupError((
                "No %(item_name)s '%(localname)s' in namespace %(namespace)s. " +
                "Available %(item_name_plural)s are: %(known_items)s"
            ) % {
                'item_name': item_name,
                'item_name_plural': item_name + 's',
                'localname': qname.localname,
                'namespace': qname.namespace,
                'known_items': known_items or ' - '
            })
