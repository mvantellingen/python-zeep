import keyword
import logging
import re

from lxml import etree

from zeep.exceptions import XMLParseError
from zeep.parser import absolute_location
from zeep.utils import as_qname, qname_attr
from zeep.xsd import elements as xsd_elements
from zeep.xsd import types as xsd_types
from zeep.xsd.const import xsd_ns
from zeep.xsd.utils import load_external

logger = logging.getLogger(__name__)


class tags(object):
    pass


for name in [
    'schema', 'import', 'include',
    'annotation', 'element', 'simpleType', 'complexType',
    'simpleContent', 'complexContent',
    'sequence', 'group', 'choice', 'all', 'list', 'union',
    'attribute', 'any', 'anyAttribute', 'attributeGroup',
    'restriction', 'extension', 'notation',

]:
    attr = name if name not in keyword.kwlist else name + '_'
    setattr(tags, attr, xsd_ns(name))


class SchemaVisitor(object):
    """Visitor which processes XSD files and registers global elements and
    types in the given schema.

    """
    def __init__(self, schema, document):
        self.document = document
        self.schema = schema
        self._includes = set()

    def process(self, node, parent):
        visit_func = self.visitors.get(node.tag)
        if not visit_func:
            raise ValueError("No visitor defined for %r" % node.tag)
        result = visit_func(self, node, parent)
        return result

    def process_ref_attribute(self, node, array_type=None):
        ref = qname_attr(node, 'ref')
        if ref:
            ref = self._create_qname(ref)

            # Some wsdl's reference to xs:schema, we ignore that for now. It
            # might be better in the future to process the actual schema file
            # so that it is handled correctly
            if ref.namespace == 'http://www.w3.org/2001/XMLSchema':
                return
            return xsd_elements.RefAttribute(
                node.tag, ref, self.schema, array_type=array_type)

    def process_reference(self, node, **kwargs):
        ref = qname_attr(node, 'ref')
        if not ref:
            return

        if node.tag == tags.element:
            cls = xsd_elements.RefElement
        elif node.tag == tags.attribute:
            cls = xsd_elements.RefAttribute
        elif node.tag == tags.group:
            cls = xsd_elements.RefGroup
        elif node.tag == tags.attributeGroup:
            cls = xsd_elements.RefAttributeGroup
        return cls(node.tag, ref, self.schema, **kwargs)

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

        self.document._target_namespace = node.get('targetNamespace')
        self.document._element_form = node.get('elementFormDefault', 'unqualified')
        self.document._attribute_form = node.get('attributeFormDefault', 'unqualified')

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
        schema_node = None
        namespace = node.get('namespace')
        location = node.get('schemaLocation')
        if location:
            location = absolute_location(location, self.document._base_url)

        if not namespace and not self.document._target_namespace:
            raise XMLParseError(
                "The attribute 'namespace' must be existent if the "
                "importing schema has no target namespace.",
                filename=self._document.location,
                sourceline=node.sourceline)

        # Check if the schema is already imported before based on the
        # namespace. Schema's without namespace are registered as 'None'
        document = self.schema._get_schema_document(namespace, location)
        if document:
            logger.debug("Returning existing schema: %r", location)
            self.document.register_import(namespace, document)
            return document

        # Hardcode the mapping between the xml namespace and the xsd for now.
        # This seems to fix issues with exchange wsdl's, see #220
        if not location and namespace == 'http://www.w3.org/XML/1998/namespace':
            location = 'https://www.w3.org/2001/xml.xsd'

        # Silently ignore import statements which we can't resolve via the
        # namespace and doesn't have a schemaLocation attribute.
        if not location:
            logger.debug(
                "Ignoring import statement for namespace %r " +
                "(missing schemaLocation)", namespace)
            return

        # Load the XML
        schema_node = load_external(location, self.schema._transport)

        # Check if the xsd:import namespace matches the targetNamespace. If
        # the xsd:import statement didn't specify a namespace then make sure
        # that the targetNamespace wasn't declared by another schema yet.
        schema_tns = schema_node.get('targetNamespace')
        if namespace and schema_tns and namespace != schema_tns:
            raise XMLParseError((
                "The namespace defined on the xsd:import doesn't match the "
                "imported targetNamespace located at %r "
                ) % (location),
                filename=self.document._location,
                sourceline=node.sourceline)

        schema = self.schema.create_new_document(schema_node, location)
        self.document.register_import(namespace, schema)
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

        if location in self._includes:
            return

        schema_node = load_external(
            location, self.schema._transport, base_url=self.document._base_url)
        self._includes.add(location)

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

        # minOccurs / maxOccurs are not allowed on global elements
        if not is_global:
            min_occurs, max_occurs = _process_occurs_attrs(node)
        else:
            max_occurs = 1
            min_occurs = 1

        # If the element has a ref attribute then all other attributes cannot
        # be present. Short circuit that here.
        # Ref is prohibited on global elements (parent = schema)
        if not is_global:
            result = self.process_reference(
                node, min_occurs=min_occurs, max_occurs=max_occurs)
            if result:
                return result

        element_form = node.get('form', self.document._element_form)
        if element_form == 'qualified' or is_global:
            qname = qname_attr(node, 'name', self.document._target_namespace)
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
                xsd_type = self._get_type(node_type.text)
            else:
                xsd_type = xsd_types.AnyType()

        # Naive workaround to mark fields which are part of a choice element
        # as optional
        if parent.tag == tags.choice:
            min_occurs = 0

        nillable = node.get('nillable') == 'true'
        default = node.get('default')
        element = xsd_elements.Element(
            name=qname, type_=xsd_type,
            min_occurs=min_occurs, max_occurs=max_occurs, nillable=nillable,
            default=default, is_global=is_global)

        self.document._elm_instances.append(element)

        # Only register global elements
        if is_global:
            self.document.register_element(qname, element)
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
        is_global = parent.tag == tags.schema

        # Check of wsdl:arayType
        array_type = node.get('{http://schemas.xmlsoap.org/wsdl/}arrayType')
        if array_type:
            match = re.match('([^\[]+)', array_type)
            if match:
                array_type = match.groups()[0]
                qname = as_qname(
                    array_type, node.nsmap, self.document._target_namespace)
                array_type = xsd_types.UnresolvedType(qname, self.schema)

        # If the elment has a ref attribute then all other attributes cannot
        # be present. Short circuit that here.
        # Ref is prohibited on global elements (parent = schema)
        if not is_global:
            result = self.process_ref_attribute(node, array_type=array_type)
            if result:
                return result

        attribute_form = node.get('form', self.document._attribute_form)
        qname = qname_attr(node, 'name', self.document._target_namespace)
        if attribute_form == 'qualified' or is_global:
            name = qname
        else:
            name = etree.QName(node.get('name'))

        annotation, items = self._pop_annotation(node.getchildren())
        if items:
            xsd_type = self.visit_simple_type(items[0], node)
        else:
            node_type = qname_attr(node, 'type')
            if node_type:
                xsd_type = self._get_type(node_type)
            else:
                xsd_type = xsd_types.AnyType()

        # TODO: We ignore 'prohobited' for now
        required = node.get('use') == 'required'
        default = node.get('default')

        attr = xsd_elements.Attribute(
            name, type_=xsd_type, default=default, required=required)
        self.document._elm_instances.append(attr)

        # Only register global elements
        if is_global:
            self.document.register_attribute(qname, attr)
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
            is_global = True
        else:
            name = parent.get('name', 'Anonymous')
            is_global = False
        base_type = '{http://www.w3.org/2001/XMLSchema}string'
        qname = as_qname(name, node.nsmap, self.document._target_namespace)

        annotation, items = self._pop_annotation(node.getchildren())
        child = items[0]
        if child.tag == tags.restriction:
            base_type = self.visit_restriction_simple_type(child, node)
            xsd_type = xsd_types.UnresolvedCustomType(
                qname, base_type, self.schema)

        elif child.tag == tags.list:
            xsd_type = self.visit_list(child, node)

        elif child.tag == tags.union:
            xsd_type = self.visit_union(child, node)
        else:
            raise AssertionError("Unexpected child: %r" % child.tag)

        assert xsd_type is not None
        if is_global:
            self.document.register_type(qname, xsd_type)
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
        base_type = '{http://www.w3.org/2001/XMLSchema}anyType'

        # If the complexType's parent is an element then this type is
        # anonymous and should have no name defined. Otherwise it's global
        if parent.tag == tags.schema:
            name = node.get('name')
            is_global = True
        else:
            name = parent.get('name')
            is_global = False

        qname = as_qname(name, node.nsmap, self.document._target_namespace)
        cls_attributes = {
            '__module__': 'zeep.xsd.dynamic_types',
            '_xsd_name': qname,
        }
        xsd_cls = type(name, (xsd_types.ComplexType,), cls_attributes)
        xsd_type = None

        # Process content
        annotation, children = self._pop_annotation(node.getchildren())
        first_tag = children[0].tag if children else None

        if first_tag == tags.simpleContent:
            base_type, attributes = self.visit_simple_content(children[0], node)

            xsd_type = xsd_cls(
                attributes=attributes, extension=base_type, qname=qname,
                is_global=is_global)

        elif first_tag == tags.complexContent:
            kwargs = self.visit_complex_content(children[0], node)
            xsd_type = xsd_cls(qname=qname, is_global=is_global, **kwargs)

        elif first_tag:
            element = None

            if first_tag in (tags.group, tags.all, tags.choice, tags.sequence):
                child = children.pop(0)
                element = self.process(child, node)

            attributes = self._process_attributes(node, children)
            xsd_type = xsd_cls(
                element=element, attributes=attributes, qname=qname,
                is_global=is_global)
        else:
            xsd_type = xsd_cls(qname=qname, is_global=is_global)

        if is_global:
            self.document.register_type(qname, xsd_type)
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
            base, element, attributes = self.visit_restriction_complex_content(
                child, node)
            return {
                'attributes': attributes,
                'element': element,
                'restriction': base,
            }
        elif child.tag == tags.extension:
            base, element, attributes = self.visit_extension_complex_content(
                child, node)
            return {
                'attributes': attributes,
                'element': element,
                'extension': base,
            }

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

    def visit_restriction_simple_type(self, node, parent, namespace=None):
        """
            <restriction
              base = QName
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (annotation?,
                (simpleType?, (
                    minExclusive | minInclusive | maxExclusive | maxInclusive |
                    totalDigits |fractionDigits | length | minLength |
                    maxLength | enumeration | whiteSpace | pattern)*))
            </restriction>
        """
        base_name = qname_attr(node, 'base')
        if base_name:
            return self._get_type(base_name)

        annotation, children = self._pop_annotation(node.getchildren())
        if children[0].tag == tags.simpleType:
            return self.visit_simple_type(children[0], node)

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
        base_name = qname_attr(node, 'base')
        base_type = self._get_type(base_name)
        return base_type, []

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
        base_name = qname_attr(node, 'base')
        base_type = self._get_type(base_name)
        annotation, children = self._pop_annotation(node.getchildren())

        element = None
        attributes = []

        if children:
            child = children[0]
            if child.tag in (tags.group, tags.all, tags.choice, tags.sequence):
                children.pop(0)
                element = self.process(child, node)
            attributes = self._process_attributes(node, children)
        return base_type, element, attributes

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
        base_type = self._get_type(base_name)
        annotation, children = self._pop_annotation(node.getchildren())

        element = None
        attributes = []

        if children:
            child = children[0]
            if child.tag in (tags.group, tags.all, tags.choice, tags.sequence):
                children.pop(0)
                element = self.process(child, node)
            attributes = self._process_attributes(node, children)

        return base_type, element, attributes

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
        base_type = self._get_type(base_name)
        annotation, children = self._pop_annotation(node.getchildren())
        attributes = self._process_attributes(node, children)

        return base_type, attributes

    def visit_annotation(self, node, parent):
        """Defines an annotation.

            <annotation
              id = ID
              {any attributes with non-schema Namespace}...>
            Content: (appinfo | documentation)*
            </annotation>
        """
        return

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
        process_contents = node.get('processContents', 'strict')
        return xsd_elements.Any(
            max_occurs=max_occurs, min_occurs=min_occurs,
            process_contents=process_contents)

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
        min_occurs, max_occurs = _process_occurs_attrs(node)
        result = xsd_elements.Sequence(
            min_occurs=min_occurs, max_occurs=max_occurs)

        annotation, items = self._pop_annotation(node.getchildren())
        for child in items:
            assert child.tag in sub_types, child
            item = self.process(child, node)
            assert item is not None
            result.append(item)

        assert None not in result
        return result

    def visit_all(self, node, parent):
        """Allows the elements in the group to appear (or not appear) in any
        order in the containing element.

            <all
              id = ID
              maxOccurs= 1: 1
              minOccurs= (0 | 1): 1
              {any attributes with non-schema Namespace...}>
            Content: (annotation?, element*)
            </all>
        """

        sub_types = [
            tags.annotation, tags.element
        ]
        result = xsd_elements.All()

        for child in node.iterchildren():
            assert child.tag in sub_types, child
            item = self.process(child, node)
            result.append(item)

        assert None not in result
        return result

    def visit_group(self, node, parent):
        """Groups a set of element declarations so that they can be
        incorporated as a group into complex type definitions.

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

        result = self.process_reference(node)
        if result:
            return result

        qname = qname_attr(node, 'name', self.document._target_namespace)

        # There should be only max nodes, first node (annotation) is irrelevant
        annotation, children = self._pop_annotation(node.getchildren())
        child = children[0]

        item = self.process(child, parent)
        elm = xsd_elements.Group(name=qname, child=item)

        if parent.tag == tags.schema:
            self.document.register_group(qname, elm)
        return elm

    def visit_list(self, node, parent):
        """
            <list
              id = ID
              itemType = QName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (simpleType?))
            </list>

        The use of the simpleType element child and the itemType attribute is
        mutually exclusive.

        """
        item_type = qname_attr(node, 'itemType')
        if item_type:
            sub_type = self._get_type(item_type.text)
        else:
            subnodes = node.getchildren()
            child = subnodes[-1]  # skip annotation
            sub_type = self.visit_simple_type(child, node)
        return xsd_types.ListType(sub_type)

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
        min_occurs, max_occurs = _process_occurs_attrs(node)

        children = node.getchildren()
        annotation, children = self._pop_annotation(children)

        choices = []
        for child in children:
            elm = self.process(child, node)
            choices.append(elm)
        return xsd_elements.Choice(
            choices, min_occurs=min_occurs, max_occurs=max_occurs)

    def visit_union(self, node, parent):
        """Defines a collection of multiple simpleType definitions.

            <union
              id = ID
              memberTypes = List of QNames
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (simpleType*))
            </union>
        """
        # TODO
        members = node.get('memberTypes')
        types = []
        if members:
            for member in members.split():
                qname = as_qname(member, node.nsmap, self.document._target_namespace)
                xsd_type = self._get_type(qname)
                types.append(xsd_type)
        else:
            annotation, types = self._pop_annotation(node.getchildren())
            types = [self.visit_simple_type(t, node) for t in types]
        return xsd_types.UnionType(types)

    def visit_unique(self, node, parent):
        """Specifies that an attribute or element value (or a combination of
        attribute or element values) must be unique within the specified scope.
        The value must be unique or nil.

            <unique
              id = ID
              name = NCName
              {any attributes with non-schema Namespace}...>
            Content: (annotation?, (selector, field+))
            </unique>
        """
        # TODO
        pass

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
        ref = self.process_reference(node)
        if ref:
            return ref

        qname = qname_attr(node, 'name', self.document._target_namespace)
        annotation, children = self._pop_annotation(node.getchildren())

        attributes = self._process_attributes(node, children)
        attribute_group = xsd_elements.AttributeGroup(qname, attributes)
        self.document.register_attribute_group(qname, attribute_group)

    def visit_any_attribute(self, node, parent):
        """
            <anyAttribute
              id = ID
              namespace = ((##any | ##other) |
                List of (anyURI | (##targetNamespace | ##local))) : ##any
              processContents = (lax | skip | strict): strict
              {any attributes with non-schema Namespace...}>
            Content: (annotation?)
            </anyAttribute>
        """
        process_contents = node.get('processContents', 'strict')
        return xsd_elements.AnyAttribute(process_contents=process_contents)

    def visit_notation(self, node, parent):
        """Contains the definition of a notation to describe the format of
        non-XML data within an XML document. An XML Schema notation declaration
        is a reconstruction of XML 1.0 NOTATION declarations.

            <notation
              id = ID
              name = NCName
              public = Public identifier per ISO 8879
              system = anyURI
              {any attributes with non-schema Namespace}...>
            Content: (annotation?)
            </notation>

        """
        pass

    def _get_type(self, name):
        assert name is not None
        name = self._create_qname(name)
        return xsd_types.UnresolvedType(name, self.schema)

    def _create_qname(self, name):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        # Handle reserved namespace
        if name.namespace == 'xml':
            name = etree.QName(
                'http://www.w3.org/XML/1998/namespace', name.localname)

        # Various xsd builders assume that some schema's are available by
        # default (actually this is mostly just the soap-enc ns). So live with
        # that fact and handle it by auto-importing the schema if it is
        # referenced.
        if (
            name.namespace == 'http://schemas.xmlsoap.org/soap/encoding/' and
            not self.document.is_imported(name.namespace)
        ):
            import_node = etree.Element(
                tags.import_,
                namespace=name.namespace, schemaLocation=name.namespace)
            self.visit_import(import_node, None)

        return name

    def _pop_annotation(self, items):
        if not len(items):
            return None, []

        if items[0].tag == tags.annotation:
            annotation = self.visit_annotation(items[0], None)
            return annotation, items[1:]
        return None, items

    def _process_attributes(self, node, items):
        attributes = []
        for child in items:
            if child.tag in (tags.attribute, tags.attributeGroup, tags.anyAttribute):
                attribute = self.process(child, node)
                attributes.append(attribute)
            else:
                raise XMLParseError(
                    "Unexpected tag `%s`" % (child.tag),
                    filename=self.document._location,
                    sourceline=node.sourceline)
        return attributes

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
        tags.all: visit_all,
        tags.group: visit_group,
        tags.attribute: visit_attribute,
        tags.import_: visit_import,
        tags.include: visit_include,
        tags.annotation: visit_annotation,
        tags.attributeGroup: visit_attribute_group,
        tags.notation: visit_notation,
    }


def _process_occurs_attrs(node):
    """Process the min/max occurrence indicators"""
    max_occurs = node.get('maxOccurs', '1')
    min_occurs = int(node.get('minOccurs', '1'))
    if max_occurs == 'unbounded':
        max_occurs = 'unbounded'
    else:
        max_occurs = int(max_occurs)

    return min_occurs, max_occurs
