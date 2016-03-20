import keyword

from lxml import etree

from zeep.parser import load_external
from zeep.utils import get_qname, parse_qname
from zeep.xsd import builtins as xsd_builtins
from zeep.xsd import elements as xsd_elements
from zeep.xsd import types as xsd_types


class tags(object):
    pass


for name in [
    'import',
    'annotation', 'element', 'simpleType', 'complexType',
    'simpleContent', 'complexContent',
    'sequence', 'group', 'choice', 'all', 'attribute', 'any',
    'restriction',

]:
    attr = name if name not in keyword.kwlist else name + '_'
    setattr(tags, attr, etree.QName('http://www.w3.org/2001/XMLSchema', name))


class SchemaVisitor(object):
    def __init__(self, schema):
        self.schema = schema
        self.elm_instances = []

    def resolve(self):
        for type_ in self.schema._types.values():
            type_.resolve(self.schema)

        for element in self.elm_instances:
            element.resolve_type(self.schema)
        self.elm_instances = []

    def process(self, node, parent, namespace):
        visit_func = self.visitors.get(node.tag)
        if not visit_func:
            raise ValueError("No visitor defined for %r", node.tag)
        result = visit_func(self, node, parent, namespace)
        return result

    def process_ref_attribute(self, node):
        ref = get_qname(
            node, 'ref', self.schema.target_namespace, as_text=False)
        if ref:
            return xsd_elements.RefElement(node.tag, ref, self.schema)

    def visit_schema(self, node):
        assert node is not None

        target_namespace = node.get('targetNamespace')
        for node in node.iterchildren():
            self.process(node, parent=None, namespace=target_namespace)

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
            Content: (annotation?, (
                      (simpleType | complexType)?, (unique | key | keyref)*))
            </element>
        """
        result = self.process_ref_attribute(node)
        if result:
            return result

        name = node.get('name')
        qname = parse_qname(name, node.nsmap, namespace)

        max_occurs = node.get('maxOccurs', '1')
        node_ref = node.get('ref')
        if node_ref:
            raise NotImplementedError()

        is_list = max_occurs == 'unbounded' or int(max_occurs) > 1
        cls = xsd_elements.Element if not is_list else xsd_elements.ListElement

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

        if not xsd_type:
            node_type = node.get('type')
            if node_type:
                type_qname = parse_qname(node_type, node.nsmap)
                try:
                    xsd_type = self.schema.get_type(type_qname)
                except KeyError:
                    xsd_type = xsd_types.UnresolvedType(type_qname)
            else:
                xsd_type = xsd_builtins.String()

        if namespace:
            nsmap = {None: namespace}
        else:
            nsmap = {}
        element = cls(name=qname, type_=xsd_type, nsmap=nsmap)
        self.elm_instances.append(element)
        self.schema.register_element(qname, element)
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

        base_type = xsd_builtins.String
        xsd_type = type(name, (base_type,), {})()
        if not is_anonymous:
            qname = parse_qname(name, node.nsmap, namespace)
            self.schema.register_type(qname, xsd_type)
        return xsd_type()

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
        Content: (annotation?, (simpleContent | complexContent |
                  ((group | all | choice | sequence)?,
                  ((attribute | attributeGroup)*, anyAttribute?))))
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
                    children = item

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

        cls = type(name, (xsd_types.ComplexType,), {})
        xsd_type = cls(elements=children, attributes=attributes)
        if not is_anonymous:
            self.schema.register_type(qname, xsd_type)
        return xsd_type

    def visit_sequence(self, node, parent, namespace):
        """
            <sequence
              id = ID
              maxOccurs = (nonNegativeInteger | unbounded) : 1
              minOccurs = nonNegativeInteger : 1
              {any attributes with non-schema Namespace}...>
            Content: (annotation?,
                      (element | group | choice | sequence | any)*)
            </sequence>
        """

        sub_types = [
            tags.annotation, tags.any, tags.choice, tags.element,
            tags.group, tags.sequence
        ]
        result = []

        for child in node.iterchildren():
            assert child.tag in sub_types, child
            item = self.process(child, node, namespace)
            result.append(item)

        assert None not in result
        return result

    def visit_attribute(self, node, parent, namespace):
        node_type = get_qname(node, 'type', namespace, as_text=False)
        if not node_type:
            assert NotImplementedError()

        name = parse_qname(node.get('name'), node.nsmap, namespace)
        try:
            xsd_type = self.schema.get_type(node_type)
        except KeyError:
            xsd_type = xsd_types.UnresolvedType(xsd_type)
        attr = xsd_elements.Attribute(name, type_=xsd_type)
        self.elm_instances.append(attr)
        return attr

    def visit_import(self, node, parent, namespace=None):
        """
            <import
              id = ID
              namespace = anyURI
              schemaLocation = anyURI
              {any attributes with non-schema Namespace}...>
            Content: (annotation?)
            </import>
        """

        if not node.get('schemaLocation'):
            raise NotImplementedError("schemaLocation is required")
        namespace = node.get('namespace')
        location = node.get('schemaLocation')

        schema_node = load_external(
            location, self.schema.transport, self.schema.schema_references)
        schema = self.schema.__class__(schema_node, self.schema.transport)
        self.schema.imports[namespace] = schema
        return schema

    def visit_restriction(self, node, namespace=None):
        pass

    def visit_annotation(self, node, parent, namespace=None):
        pass

    def visit_group(self, node, parent, namespace=None):
        """
            <group
              name= NCName
              id = ID
              maxOccurs = (nonNegativeInteger | unbounded) : 1
              minOccurs = nonNegativeInteger : 1
              name = NCName
              ref = QName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (all | choice | sequence))
            </group>
        """

        result = self.process_ref_attribute(node)
        if result:
            return result

        qname = get_qname(node, 'name', namespace, as_text=False)

        # There should be only max nodes, first node (annotation) is irrelevant
        subnodes = node.getchildren()
        child = subnodes[-1]
        children = self.process(child, parent, namespace)

        elm = xsd_elements.GroupElement(name=qname, children=children)
        self.schema.register_element(qname, elm)
        return elm

    def visit_list(self, node, parent, namespace=None):
        """
            <list
              id = ID
              itemType = QName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (simpleType?))
            </list>

        """
        raise NotImplementedError()

    def visit_union(self, node, parent, namespace=None):
        """
            <union
              id = ID
              memberTypes = List of QNames
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (simpleType*))
            </union>
        """
        raise NotImplementedError()

    def visit_unique(self, node, parent, namespace=None):
        """
            <unique
              id = ID
              name = NCName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (selector, field+))
            </unique>
        """
        raise NotImplementedError()

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
