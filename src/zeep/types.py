import keyword
import logging

from lxml import etree

from zeep import xsd
from zeep.parser import load_external
from zeep.utils import parse_qname

NSMAP = {
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
}

logger = logging.getLogger(__name__)


def element_maker(name):
    return etree.QName('{%s}%s' % (NSMAP['xsd'], name))


class tags(object):
    pass


for name in [
    'import',
    'annotation', 'element', 'simpleType', 'complexType',
    'simpleContent', 'complexContent',
    'sequence', 'group', 'choice', 'all', 'attribute', 'any',
    'restriction',

]:
    kwname = name if name not in keyword.kwlist else name + '_'
    setattr(tags, kwname, element_maker(name))


class Schema(object):

    def __init__(self, node=None, references=None):

        self.schema_references = references or {}

        self.types = {}
        self.elements = {}
        self.elm_instances = []

        if node:
            self.xml_schema = etree.XMLSchema(node)
            self.target_namespace = node.get('targetNamespace')
            self.visit_schema(node)
            for element in self.elm_instances:
                element.resolve_type(self)

    def register_type(self, name, value):
        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_type(%r, %r)", name, value)
        self.types[name] = value

    def register_element(self, name, value):
        if isinstance(name, etree.QName):
            name = name.text
        logger.debug("register_element(%r, %r)", name, value)
        self.elements[name] = value

    def get_type(self, name):
        if isinstance(name, etree.QName):
            name = name.text

        if name in xsd.default_types:
            return xsd.default_types[name]

        if name not in self.types:
            raise KeyError(
                "No such type: %r (Only have %s)" % (
                    name, ', '.join(self.elements)))
        return self.types[name]

    def get_element(self, name):
        if isinstance(name, etree.QName):
            name = name.text

        if name not in self.elements:
            raise KeyError(
                "No such element: %r (Only have %s)" % (
                    name, ', '.join(self.elements)))
        return self.elements[name]

    def custom_type(self, name):
        return self.get_type(name)

    def visit_schema(self, node):
        assert node is not None

        target_namespace = node.get('targetNamespace')
        for node in node.iterchildren():
            self.process(node, parent=None, namespace=target_namespace)

    def process(self, node, parent, namespace):
        visit_func = self.visitors.get(node.tag)
        if not visit_func:
            raise ValueError("No visitor defined for %r", node.tag)
        return visit_func(self, node, parent, namespace)

    def visit_element(self, node, parent, namespace=None):
        """
            <element
              abstract = Boolean : false
              block = (#all | List of (extension | restriction | substitution))
              default = string
              final = (#all | List of (extension | restriction))
              fixed = string
              form = (qualified | unqualified)
              id = ID
              maxOccurs = (nonNegativeInteger | unbounded) : 1
              minOccurs = nonNegativeInteger : 1
              name = NCName
              nillable = Boolean : false
              ref = QName
              substitutionGroup = QName
              type = QName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, ((simpleType | complexType)?, (unique | key |
            keyref)*))
            </element>
        """
        name = node.get('name')
        qname = parse_qname(name, node.nsmap, namespace)

        max_occurs = node.get('maxOccurs', '1')
        node_ref = node.get('ref')
        if node_ref:
            raise NotImplementedError()

        is_list = max_occurs == 'unbounded' or int(max_occurs) > 1
        cls = xsd.Element if not is_list else xsd.ListElement

        children = node.getchildren()
        xsd_type = None
        if children:
            value = None

            for child in children:
                if child.tag == tags.annotation:
                    continue

                elif child.tag in (tags.simpleType, tags.complexType):
                    assert not value

                    xsd_type = self.process(child, node, namespace)
                    xsd_type = xsd_type()

        if not xsd_type:
            node_type = node.get('type')
            if node_type:
                type_qname = parse_qname(node_type, node.nsmap)
                try:
                    xsd_type = self.get_type(type_qname)()
                except KeyError:
                    xsd_type = xsd.UnresolvedType(type_qname)
            else:
                xsd_type = xsd.String()

        if namespace:
            nsmap = {None: namespace}
        else:
            nsmap = {}
        element = cls(name=name, type_=xsd_type, nsmap=nsmap)
        self.elm_instances.append(element)

        self.register_element(qname, element)
        return element

    def visit_simple_type(self, node, parent, namespace=None):
        """
            <simpleType
              final = (#all | (list | union | restriction))
              id = ID
              name = NCName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (restriction | list | union))
            </simpleType>
        """

        if parent is None:
            name = node.get('name')
            is_anonymous = False
        else:
            name = parent.get('name')
            is_anonymous = True

        for child in node.iterchildren():
            if child.tag == tags.annotation:
                continue

            elif child.tag == tags.restriction:
                break

            elif child.tag == tags.list:
                break

            elif child.tag == tags.union:
                break

        xsd_type = xsd.String
        if not is_anonymous:
            qname = parse_qname(name, node.nsmap, namespace)
            self.register_type(qname, xsd_type)
        return xsd_type

    def visit_complex_type(self, node, parent, namespace=None):
        """
        <complexType
          abstract = Boolean : false
          block = (#all | List of (extension | restriction))
          final = (#all | List of (extension | restriction))
          id = ID
          mixed = Boolean : false
          name = NCName
          {any attributes with non-schema Namespace...}>
        Content: (annotation?, (simpleContent | complexContent | ((group | all |
        choice | sequence)?, ((attribute | attributeGroup)*, anyAttribute?))))
        </complexType>

        """
        attributes = []
        children = []

        for child in node.iterchildren():
            if child.tag == tags.annotation:
                continue

            elif child.tag == tags.simpleContent:
                break

            elif child.tag == tags.complexContent:
                break

            else:
                item = self.process(child, node, namespace)

                if child.tag == tags.group:
                    assert not children

                elif child.tag in (tags.choice, tags.sequence, tags.all):
                    assert not children
                    children = item

                elif child.tag in (tags.attribute,):
                    attributes.append(item)

        # If the complexType's parent is an element then this type is
        # anonymous and should have no name defined.
        if parent is None:
            name = node.get('name')
            is_anonymous = False
        else:
            name = parent.get('name')
            is_anonymous = True

        qname = parse_qname(name, node.nsmap, namespace)
        cls = type(name, (xsd.ComplexType,), {})
        cls.__metadata__ = {
            'fields': children + attributes
        }
        xsd_type = cls
        if not is_anonymous:
            self.register_type(qname, xsd_type)
        return xsd_type

    def visit_sequence(self, node, parent, namespace):
        sub_types = [
            tags.annotation, tags.any, tags.choice, tags.element,
            tags.group, tags.sequence
        ]
        result = []

        for child in node.iterchildren():
            assert child.tag in sub_types, child
            item = self.process(child, node, namespace)
            result.append(item)
        return result

    def visit_attribute(self, node, parent, namespace):
        node_type = node.get('type')
        if node_type:
            xml_type = parse_qname(node_type, node.nsmap)
        else:
            assert NotImplementedError()

        name = node.get('name')
        try:
            xsd_type = self.get_type(node_type)()
        except KeyError:
            xsd_type = xsd.UnresolvedType(xml_type)
        attr = xsd.Attribute(name, type_=xsd_type)
        self.elm_instances.append(attr)
        return attr

    def visit_import(self, node, parent, namespace=None):
        if not node.get('schemaLocation'):
            raise NotImplementedError("schemaLocation is required")
        namespace = 'intschema+%s' % node.get('namespace')

        location = node.get('schemaLocation')
        if location.startswith('intschema+'):
            schema_node = self.schema_references[namespace]
            return self.visit_schema(schema_node)

        schema_node = load_external(location, self.schema_references)
        return self.visit_schema(schema_node)

    def visit_restriction(self, node, namespace=None):
        pass

    def visit_annotation(self, node, parent, namespace=None):
        pass

    def visit_group(self, node, parent, namespace=None):
        pass

    visitors = {
        tags.element: visit_element,
        tags.simpleType: visit_simple_type,
        tags.complexType: visit_complex_type,
        tags.simpleContent: None,
        tags.complexContent: None,
        tags.sequence: visit_sequence,
        tags.all: visit_sequence,
        tags.group: visit_group,
        tags.attribute: visit_attribute,
        tags.import_: visit_import,
        tags.restriction: visit_restriction,
        tags.annotation: visit_annotation,
    }
