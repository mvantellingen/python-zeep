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
    'schema', 'import',
    'annotation', 'element', 'simpleType', 'complexType',
    'simpleContent', 'complexContent',
    'sequence', 'group', 'choice', 'all', 'attribute', 'any',
    'restriction', 'extension',

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

    def process(self, node, parent):
        visit_func = self.visitors.get(node.tag)
        if not visit_func:
            raise ValueError("No visitor defined for %r", node.tag)
        result = visit_func(self, node, parent)
        return result

    def process_ref_attribute(self, node):
        ref = get_qname(
            node, 'ref', self.schema.target_namespace, as_text=False)
        if ref:
            return xsd_elements.RefElement(node.tag, ref, self.schema)

    def visit_schema(self, node):
        """
            <schema
              attributeFormDefault = (qualified | unqualified): unqualified
              blockDefault = (#all | List of (extension | restriction | substitution) : ''
              elementFormDefault = (qualified | unqualified): unqualified
              finalDefault = (#all | List of (extension | restriction | list | union): ''
              id = ID
              targetNamespace = anyURI
              version = token
              xml:lang = language
              {any attributes with non-schema Namespace}...>
            Content: (
                (include | import | redefine | annotation)*,
                (((simpleType | complexType | group | attributeGroup) |
                  element | attribute | notation),
                 annotation*)*)
            </schema>

        """
        assert node is not None

        self.schema.target_namespace = node.get('targetNamespace')
        self.schema.element_form = node.get('elementFormDefault', 'unqualified')
        self.schema.attribute_form = node.get('attributeFormDefault', 'unqualified')
        parent = node
        for node in node.iterchildren():
            self.process(node, parent=parent)

    def visit_import(self, node, parent):
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

    def visit_element(self, node, parent):
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
        is_global = parent.tag == tags.schema

        # If the elment has a ref attribute then all other attributes cannot
        # be present. Short circuit that here.
        # Ref is prohibited on global elements (parent = schema)
        if not is_global:
            result = self.process_ref_attribute(node)
            if result:
                return result

        name = node.get('name')
        element_form = node.get('form', self.schema.element_form)
        if element_form == 'qualified' or is_global:
            qname = parse_qname(name, node.nsmap, self.schema.target_namespace)
        else:
            qname = etree.QName(name)

        children = node.getchildren()
        xsd_type = None
        if children:
            value = None

            for child in children:
                if child.tag == tags.annotation:
                    continue

                elif child.tag in (tags.simpleType, tags.complexType):
                    assert not value

                    xsd_type = self.process(child, node)

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

        # minOccurs / maxOccurs are not allowed on global elements
        if not is_global:
            max_occurs = node.get('maxOccurs', '1')
            is_list = max_occurs == 'unbounded' or int(max_occurs) > 1
        else:
            max_occurs = 1
            is_list = False

        cls = xsd_elements.Element if not is_list else xsd_elements.ListElement
        element = cls(name=qname, type_=xsd_type)

        self.elm_instances.append(element)

        # Only register global elements
        if is_global:
            self.schema.register_element(qname, element)
        return element

    def visit_attribute(self, node, parent):
        """Declares an attribute.

            <attribute
              default = string
              fixed = string
              form = (qualified | unqualified)
              id = ID
              name = NCName
              ref = QName
              type = QName
              use = (optional | prohibited | required): optional
              {any attributes with non-schema Namespace...}>
            Content: (annotation?, (simpleType?))
            </attribute>
        """
        node_type = get_qname(
            node, 'type', self.schema.target_namespace, as_text=False)
        if not node_type:
            assert NotImplementedError()

        attribute_form = node.get('form', self.schema.attribute_form)
        if attribute_form == 'qualified':
            name = parse_qname(
                node.get('name'), node.nsmap,  self.schema.target_namespace)
        else:
            name = etree.QName(node.get('name'))

        try:
            xsd_type = self.schema.get_type(node_type)
        except KeyError:
            xsd_type = xsd_types.UnresolvedType(node_type)
        attr = xsd_elements.Attribute(name, type_=xsd_type)
        self.elm_instances.append(attr)
        return attr

    def visit_simple_type(self, node, parent):
        """
            <simpleType
              final = (#all | (list | union | restriction))
              id = ID
              name = NCName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (restriction | list | union))
            </simpleType>
        """

        if parent.tag == tags.schema:
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
                self.visit_list(child, node)

            elif child.tag == tags.union:
                self.visit_list(child, node)

        base_type = xsd_builtins.String
        xsd_type = type(name, (base_type,), {})()
        if not is_anonymous:
            qname = parse_qname(name, node.nsmap, self.schema.target_namespace)
            self.schema.register_type(qname, xsd_type)
        return xsd_type()

    def visit_complex_type(self, node, parent):
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
        children = []

        for child in node.iterchildren():
            if child.tag == tags.annotation:
                continue

            elif child.tag == tags.simpleContent:
                children = self.visit_simple_content(child, node)

            elif child.tag == tags.complexContent:
                children = self.visit_complex_content(child, node)

            else:
                item = self.process(child, node)

                if child.tag == tags.group:
                    assert not children
                    children = item

                elif child.tag in (tags.choice, tags.sequence, tags.all):
                    assert not children
                    children = item

                elif child.tag in (tags.attribute,):
                    children.append(item)

        # If the complexType's parent is an element then this type is
        # anonymous and should have no name defined.
        if parent.tag == tags.schema:
            name = node.get('name')
            is_anonymous = False
        else:
            name = parent.get('name')
            is_anonymous = True

        qname = parse_qname(name, node.nsmap, self.schema.target_namespace)

        cls = type(
            name, (xsd_types.ComplexType,), {'__module__': 'zeep.xsd.types'})
        xsd_type = cls(children)

        if not is_anonymous:
            self.schema.register_type(qname, xsd_type)
        return xsd_type

    def visit_complex_content(self, node, parent, namespace=None):
        """The complexContent element defines extensions or restrictions on a
        complex type that contains mixed content or elements only.

            <complexContent
              id = ID
              mixed = Boolean
              {any attributes with non-schema Namespace}...>
            Content: (annotation?,  (restriction | extension))
            </complexContent>
        """

        child = node.getchildren()[-1]

        if child.tag == tags.restriction:
            return self.visit_restriction_complex_content(child, node)

        if child.tag == tags.extension:
            return self.visit_extension_complex_content(child, node)

    def visit_simple_content(self, node, parent, namespace=None):
        """Contains extensions or restrictions on a complexType element with
        character data or a simpleType element as content and contains no
        elements.

            <simpleContent
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (restriction | extension))
            </simpleContent>
        """

        child = node.getchildren()[-1]

        if child.tag == tags.restriction:
            return self.visit_restriction_simple_content(child, node)
        elif child.tag == tags.extension:
            return self.visit_extension_simple_content(child, node)
        raise AssertionError("Expected restriction or extension")

    def visit_restriction_complex_content(self, node, parent, namespace=None):
        """

            <restriction
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (group | all | choice | sequence)?,
                    ((attribute | attributeGroup)*, anyAttribute?))
            </restriction>
        """
        pass

    def visit_restriction_simple_content(self, node, parent, namespace=None):
        """
            <restriction
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?,
                (simpleType?, (
                    minExclusive | minInclusive | maxExclusive | maxInclusive |
                    totalDigits |fractionDigits | length | minLength |
                    maxLength | enumeration | whiteSpace | pattern)*
                )?, ((attribute | attributeGroup)*, anyAttribute?))
            </restriction>
        """
        pass

    def visit_extension_complex_content(self, node, parent):
        """
            <extension
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (
                        (group | all | choice | sequence)?,
                        ((attribute | attributeGroup)*, anyAttribute?)))
            </extension>
        """
        base_name = get_qname(node, 'base', self.schema.target_namespace)
        try:
            base = self.schema.get_type(base_name)
            children = base._children
        except KeyError:
            children = [xsd_types.UnresolvedType(base_name)]

        for child in node.iterchildren():
            if child.tag == tags.annotation:
                continue

            item = self.process(child, node)

            if child.tag == tags.group:
                children.extend(item)

            elif child.tag in (tags.choice, tags.sequence, tags.all):
                children.extend(item)

            elif child.tag in (tags.attribute,):
                children.append(item)

        return children

    def visit_extension_simple_content(self, node, parent):
        """
            <extension
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, ((attribute | attributeGroup)*, anyAttribute?))
            </extension>
        """
        base_name = get_qname(node, 'base', self.schema.target_namespace)
        try:
            base = self.schema.get_type(base_name)
            if isinstance(base, xsd_types.ComplexType):
                children = base._children
            else:
                children = [base]
        except KeyError:
            raise
            children = [xsd_types.UnresolvedType(base_name)]

        for child in node.iterchildren():
            if child.tag == tags.annotation:
                continue

            item = self.process(child, node)
            if child.tag in (tags.attribute,):
                children.append(item)

        return children

    def visit_annotation(self, node, parent):
        """Defines an annotation.

            <annotation
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (appinfo | documentation)*
            </annotation>
        """
        pass

    def visit_sequence(self, node, parent):
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
            item = self.process(child, node)
            result.append(item)

        assert None not in result
        return result

    def visit_group(self, node, parent):
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

        qname = get_qname(
            node, 'name', self.schema.target_namespace, as_text=False)

        # There should be only max nodes, first node (annotation) is irrelevant
        subnodes = node.getchildren()
        child = subnodes[-1]
        children = self.process(child, parent)

        elm = xsd_elements.GroupElement(name=qname, children=children)

        if parent.tag == tags.schema:
            self.schema.register_element(qname, elm)
        return elm

    def visit_list(self, node, parent):
        """
            <list
              id = ID
              itemType = QName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (simpleType?))
            </list>

        """
        raise NotImplementedError()

    def visit_union(self, node, parent):
        """
            <union
              id = ID
              memberTypes = List of QNames
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (simpleType*))
            </union>
        """
        raise NotImplementedError()

    def visit_unique(self, node, parent):
        """
            <unique
              id = ID
              name = NCName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (selector, field+))
            </unique>
        """
        raise NotImplementedError()

    def visit_attribute_group(self, node, parent):
        """
            <attributeGroup
              id = ID
              name = NCName
              ref = QName
              {any attributes with non-schema Namespace...}>
            Content: (annotation?),
                     ((attribute | attributeGroup)*, anyAttribute?))
            </attributeGroup>
        """
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
        tags.annotation: visit_annotation,
    }
