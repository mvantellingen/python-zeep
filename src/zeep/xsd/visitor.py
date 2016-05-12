import keyword
import logging

from lxml import etree

from zeep.parser import absolute_location, load_external
from zeep.utils import as_qname, qname_attr
from zeep.xsd import builtins as xsd_builtins
from zeep.xsd import elements as xsd_elements
from zeep.xsd import types as xsd_types

logger = logging.getLogger(__name__)


class tags(object):
    pass


for name in [
    'schema', 'import', 'include',
    'annotation', 'element', 'simpleType', 'complexType',
    'simpleContent', 'complexContent',
    'sequence', 'group', 'choice', 'all', 'attribute', 'any', 'anyAttribute',
    'restriction', 'extension',

]:
    attr = name if name not in keyword.kwlist else name + '_'
    setattr(tags, attr, etree.QName('http://www.w3.org/2001/XMLSchema', name))


class SchemaVisitor(object):
    def __init__(self, schema, parser_context=None):
        self.schema = schema
        self.parser_context = parser_context

    def process(self, node, parent):
        visit_func = self.visitors.get(node.tag)
        if not visit_func:
            raise ValueError("No visitor defined for %r" % node.tag)
        result = visit_func(self, node, parent)
        return result

    def process_ref_attribute(self, node):
        ref = qname_attr(node, 'ref')
        if ref:

            # Some wsdl's reference to xs:schema, we ignore that for now. It
            # might be better in the future to process the actual schema file
            # so that it is handled correctly
            if ref.namespace == 'http://www.w3.org/2001/XMLSchema':
                return
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

        self.schema._target_namespace = node.get('targetNamespace')
        self.schema._element_form = node.get('elementFormDefault', 'unqualified')
        self.schema._attribute_form = node.get('attributeFormDefault', 'unqualified')

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

        # Resolve import if it is a file
        location = absolute_location(location, self.schema._base_url)
        schema = self.parser_context.schema_objects.get(location)
        if schema:
            logger.debug("Returning existing schema: %r", location)
            self.schema._imports[namespace] = schema
            return schema

        schema_node = load_external(
            location, self.schema._transport, self.parser_context)

        # If this schema location is 'internal' then retrieve the original
        # location since that is used as base url for sub include/imports
        if location in self.parser_context.schema_locations:
            base_url = self.parser_context.schema_locations[location]
        else:
            base_url = location

        schema = self.schema.__class__(
            schema_node, self.schema._transport, location,
            self.parser_context, base_url)

        self.schema._imports[namespace] = schema
        return schema

    def visit_include(self, node, parent):
        """
        <include
          id = ID
          schemaLocation = anyURI
          {any attributes with non-schema Namespace}...>
        Content: (annotation?)
        </include>
        """
        if not node.get('schemaLocation'):
            raise NotImplementedError("schemaLocation is required")
        location = node.get('schemaLocation')

        schema_node = load_external(
            location, self.schema._transport, self.parser_context,
            base_url=self.schema._base_url)
        return self.visit_schema(schema_node)

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

        element_form = node.get('form', self.schema._element_form)
        if element_form == 'qualified' or is_global:
            qname = qname_attr(node, 'name', self.schema._target_namespace)
        else:
            qname = etree.QName(node.get('name'))

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
            node_type = qname_attr(node, 'type')
            if node_type:
                try:
                    xsd_type = self.schema.get_type(node_type.text)
                except KeyError:
                    xsd_type = xsd_types.UnresolvedType(node_type.text)
            else:
                xsd_type = xsd_builtins.String()

        # minOccurs / maxOccurs are not allowed on global elements
        if not is_global:
            min_occurs, max_occurs = _process_occurs_attrs(node)
        else:
            max_occurs = 1
            min_occurs = 1

        nillable = node.get('nillable') == 'true'
        cls = xsd_elements.Element if max_occurs == 1 else xsd_elements.ListElement
        element = cls(
            name=qname, type_=xsd_type,
            min_occurs=min_occurs, max_occurs=max_occurs, nillable=nillable)

        self.schema._elm_instances.append(element)

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
        attribute_form = node.get('form', self.schema._attribute_form)
        if attribute_form == 'qualified':
            name = qname_attr(node, 'name', self.schema._target_namespace)
        else:
            name = etree.QName(node.get('name'))

        xsd_type = None
        for child in node.iterchildren():
            if child.tag == tags.annotation:
                continue

            elif child.tag == tags.simpleType:
                assert xsd_type is None
                xsd_type = self.visit_simple_type(child, node)

        if xsd_type is None:
            node_type = qname_attr(node, 'type')
            try:
                xsd_type = self.schema.get_type(node_type)
            except KeyError:
                xsd_type = xsd_types.UnresolvedType(node_type)

        attr = xsd_elements.Attribute(name, type_=xsd_type)
        self.schema._elm_instances.append(attr)
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
            qname = as_qname(name, node.nsmap, self.schema._target_namespace)
            self.schema.register_type(qname, xsd_type)
        return xsd_type

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

                    # XXX: Not good
                    if not isinstance(item, list):
                        item = [item]

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

        qname = as_qname(name, node.nsmap, self.schema._target_namespace)

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
        base_name = qname_attr(node, 'base')
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
        base_name = qname_attr(node, 'base')
        try:
            base = self.schema.get_type(base_name)
            if isinstance(base, xsd_types.ComplexType):
                children = base._children
            else:
                children = [xsd_types.Element(None, base)]
        except KeyError:
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

    def visit_any(self, node, parent):
        """
            <any
              id = ID
              maxOccurs = (nonNegativeInteger | unbounded) : 1
              minOccurs = nonNegativeInteger : 1
              namespace = "(##any | ##other) |
                List of (anyURI | (##targetNamespace |  ##local))) : ##any
              processContents = (lax | skip | strict) : strict
              {any attributes with non-schema Namespace...}>
            Content: (annotation?)
            </any>
        """
        min_occurs, max_occurs = _process_occurs_attrs(node)
        return xsd_elements.Any(max_occurs=max_occurs, min_occurs=min_occurs)

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

        qname = qname_attr(node, 'name', self.schema._target_namespace)

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

    def visit_choice(self, node, parent):
        """
            <choice
              id = ID
              maxOccurs= (nonNegativeInteger | unbounded) : 1
              minOccurs= nonNegativeInteger : 1
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (element | group | choice | sequence | any)*)
            </choice>
        """
        # There should be only max nodes, first node (annotation) is irrelevant
        children = node.getchildren()
        if children[0].tag == tags.annotation:
            children.pop(0)

        choices = []
        for child in children:
            elm = self.process(child, node)
            elm.min_occurs = 0
            choices.append(elm)
        return xsd_elements.Choice(choices)

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

    def visit_any_attribute(self, node, parent):
        pass

    visitors = {
        tags.any: visit_any,
        tags.element: visit_element,
        tags.choice: visit_choice,
        tags.simpleType: visit_simple_type,
        tags.anyAttribute: visit_any_attribute,
        tags.complexType: visit_complex_type,
        tags.simpleContent: None,
        tags.complexContent: None,
        tags.sequence: visit_sequence,
        tags.all: visit_sequence,
        tags.group: visit_group,
        tags.attribute: visit_attribute,
        tags.import_: visit_import,
        tags.include: visit_include,
        tags.annotation: visit_annotation,
    }


def _process_occurs_attrs(node):
    max_occurs = node.get('maxOccurs', '1')
    min_occurs = int(node.get('minOccurs', '1'))
    if max_occurs == 'unbounded':
        max_occurs = None
    else:
        max_occurs = int(max_occurs)

    return min_occurs, max_occurs
