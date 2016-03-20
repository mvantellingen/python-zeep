from decimal import Decimal as _Decimal

from lxml import etree

from zeep.utils import process_signature


class Type(object):

    def accept(self, value):
        raise NotImplementedError

    def parse_xmlelement(self, xmlelement):
        raise NotImplementedError

    def parsexml(self, xml):
        raise NotImplementedError

    def render(self, parent, value):
        raise NotImplementedError

    def resolve(self):
        raise NotImplementedError

    @classmethod
    def signature(cls):
        return ''


class UnresolvedType(Type):
    def __init__(self, qname):
        self.qname = qname

    def resolve(self, schema):
        return schema.get_type(self.qname)


class SimpleType(Type):

    def render(self, parent, value):
        parent.text = self.xmlvalue(value)

    def parse_xmlelement(self, xmlelement):
        return self.pythonvalue(xmlelement.text)

    def xmlvalue(self, value):
        raise NotImplementedError

    def pythonvalue(self, xmlvalue):
        raise NotImplementedError

    def resolve(self):
        pass

    def __call__(self, *args, **kwargs):
        if args:
            return unicode(args[0])
        return u''

    def __str__(self):
        return self.name

    def __unicode__(self):
        return unicode(self.name)


class ComplexType(Type):

    def __init__(self, elements=None, attributes=None):
        self._elements = elements or []
        self._attributes = attributes or []

    def properties(self):
        return list(self._elements) + list(self._attributes)

    def render(self, parent, value):
        for element in self.properties():
            sub_value = getattr(value, element.name)
            element.render(parent, sub_value)

    def __call__(self, *args, **kwargs):
        if not hasattr(self, '_value_class'):
            self._value_class = type(
                self.__class__.__name__ + 'Object', (CompoundValue,),
                {'type': self, '__module__': 'zeep.objects'})

        return self._value_class(*args, **kwargs)

    def resolve(self):
        elements = []
        for elm in self._elements:
            if isinstance(elm, RefElement):
                elm = elm._elm

            if isinstance(elm, GroupElement):
                elements.extend(list(elm))
            else:
                elements.append(elm)
        self._elements = elements

    def signature(self):
        return ', '.join(
            ['%s %s' % (prop.type.name, prop.name) for prop in self.properties()
        ])

    def parse_xmlelement(self, xmlelement):
        instance = self()
        fields = self.properties()
        if not fields:
            return instance

        elements = xmlelement.getchildren()
        fields = iter(fields)
        field = next(fields)
        for element in elements:
            if field.qname != element.tag:
                field = next(fields, None)

            if not field:
                break

            if field.qname != element.tag:
                # XXX Element might be optional
                raise ValueError("Unexpected element: %r" % element.tag)

            result = field.parse(element)
            if isinstance(field, ListElement):
                getattr(instance, field.name).append(result)
            else:
                setattr(instance, field.name, result)

        return instance

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self.signature())


class AnyType(SimpleType):
    name = 'xsd:anyType'

    def xmlvalue(self, value):
        return unicode(value)

    def pythonvalue(self, value):
        return unicode(value)


class AnyURI(SimpleType):
    name = 'xsd:anyURI'

    def xmlvalue(self, value):
        return unicode(value)

    def pythonvalue(self, value):
        return unicode(value)


class String(SimpleType):
    name = 'xsd:string'

    def xmlvalue(self, value):
        return unicode(value)

    def pythonvalue(self, value):
        return unicode(value)


class ID(String):
    name = 'xsd:ID'


class IDREF(ID):
    name = 'xsd:IDREF'


class Byte(String):
    name = 'xsd:byte'


class Base64Binary(String):
    name = 'xsd:base64Binary'


class QName(String):
    name = 'xsd:QName'


class Boolean(SimpleType):
    name = 'xsd:boolean'

    def xmlvalue(self, value):
        return 'true' if value else 'false'

    def pythonvalue(self, value):
        return value in ('true', '1')


class DateTime(SimpleType):
    def xmlvalue(self, value):
        return value.strftime('%Y-%m-%dT%H:%M:%S')

    def pythonvalue(self, value):
        return value


class Double(SimpleType):
    name = 'xsd:double'

    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return float(value)


class Float(SimpleType):
    name = 'xsd:float'

    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return float(value)


class Decimal(SimpleType):
    name = 'xsd:decimal'

    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return _Decimal(value)


class Integer(Decimal):
    name = 'xsd:integer'

    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return int(value)

class Short(Integer):
    name = 'xsd:short'


class Long(Integer):
    name = 'xsd:long'


class UnsignedShort(Short):
    name = 'xsd:UnsignedShort'


class UnsignedLong(Integer):
    name = 'xsd:UnsignedLong'


class UnsignedInt(Integer):
    name = 'xsd:UnsignedInt'


class Element(object):
    def __init__(self, name, type_=None, nsmap=None):
        self.name = name.localname
        self.qname = name
        self.type = type_
        self.nsmap = nsmap or {}
        # assert type_

    def __repr__(self):
        return '<%s(name=%r, type=%r)>' % (
            self.__class__.__name__, self.name, self.type)

    def resolve_type(self, schema):
        if isinstance(self.type, UnresolvedType):
            self.type = self.type.resolve(schema)

    def render(self, parent, value):
        assert parent is not None
        assert self.name is not None
        assert self.nsmap is not None

        node = etree.SubElement(parent, self.qname, nsmap=self.nsmap)
        return self.type.render(node, value)

    def parse(self, value):
        return self.type.parse_xmlelement(value)

    def __call__(self, *args, **kwargs):
        return self.type(*args, **kwargs)


class Attribute(Element):
    def render(self, parent, value):
        value = self.type.xmlvalue(value)
        parent.set(self.name, value)


class ListElement(Element):
    def __call__(self, *args, **kwargs):
        return []

    def render(self, parent, value):
        for val in value:
            node = etree.SubElement(parent, self.name)
            self.type.render(node, val)


class GroupElement(Element):
    def __init__(self, *args, **kwargs):
        self.children = kwargs.pop('children', [])
        assert self.children
        super(GroupElement, self).__init__(*args, **kwargs)

    def __iter__(self, *args, **kwargs):
        for item in self.properties():
            yield item

    def properties(self):
        return self.children


class CompoundValue(object):

    def __init__(self, *args, **kwargs):
        properties = {
            prop.name: prop() for prop in self.type.properties()
        }
        property_names = [prop.name for prop in self.type.properties()]

        # Set default values
        for key, value in properties.iteritems():
            setattr(self, key, value)

        items = process_signature(property_names, args, kwargs)
        for key, value in items.iteritems():
            setattr(self, key, value)


class RefElement(object):

    def __init__(self, tag, ref, wsdl):
        self._ref = ref
        self._wsdl = wsdl

    @property
    def _elm(self):
        return self._wsdl.get_element(self._ref)

    def __iter__(self, *args, **kwargs):
        elm = self._elm
        for item in elm.properties():
            yield item

    def __call__(self, *args, **kwargs):
        return self._elm(*args, **kwargs)

    def __getattr__(self, name):
        if not name.startswith('_'):
            return getattr(self._elm, name)
        return getattr(self, name)


default_types = {
    '{http://www.w3.org/2001/XMLSchema}anyType': AnyType(),
    '{http://www.w3.org/2001/XMLSchema}anyURI': AnyURI(),
    '{http://www.w3.org/2001/XMLSchema}ID': ID(),
    '{http://www.w3.org/2001/XMLSchema}IDREF': IDREF(),
    '{http://www.w3.org/2001/XMLSchema}byte': Byte(),
    '{http://www.w3.org/2001/XMLSchema}short': Short(),
    '{http://www.w3.org/2001/XMLSchema}unsignedByte': String(),
    '{http://www.w3.org/2001/XMLSchema}unsignedInt': UnsignedInt(),
    '{http://www.w3.org/2001/XMLSchema}unsignedLong': UnsignedLong(),
    '{http://www.w3.org/2001/XMLSchema}unsignedShort': UnsignedShort(),
    '{http://www.w3.org/2001/XMLSchema}QName': QName(),
    '{http://www.w3.org/2001/XMLSchema}string': String(),
    '{http://www.w3.org/2001/XMLSchema}float': Float(),
    '{http://www.w3.org/2001/XMLSchema}int': Integer(),
    '{http://www.w3.org/2001/XMLSchema}long': Long(),
    '{http://www.w3.org/2001/XMLSchema}base64Binary': Base64Binary(),
    '{http://www.w3.org/2001/XMLSchema}boolean': Boolean(),
    '{http://www.w3.org/2001/XMLSchema}decimal': Decimal(),
    '{http://www.w3.org/2001/XMLSchema}dateTime': DateTime(),
    '{http://www.w3.org/2001/XMLSchema}double': Double(),
}
