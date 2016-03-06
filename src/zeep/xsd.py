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

    def __unicode__(self):
        return '%s(%s)' % (self.__class__.__name__, self.signature())

    @classmethod
    def signature(cls):
        return ''


class UnresolvedType(Type):
    def __init__(self, qname):
        self.qname = qname

    def resolve(self, schema):
        return schema.get_type(self.qname)()


class SimpleType(Type):

    def render(self, parent, value):
        parent.text = self.xmlvalue(value)

    def parse_xmlelement(self, xmlelement):
        return self.pythonvalue(xmlelement.text)

    def xmlvalue(self, value):
        raise NotImplementedError

    def pythonvalue(self, xmlvalue):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        if args:
            return unicode(args[0])
        return u''


class ComplexType(Type):

    @classmethod
    def properties(cls):
        return cls.__metadata__['fields']

    def render(self, parent, value):
        for element in self.__metadata__['fields']:
            sub_value = getattr(value, element.name)
            element.render(parent, sub_value)

    def __call__(self, *args, **kwargs):
        if not hasattr(self, '_value_class'):
            self._value_class = type(
                self.__class__.__name__, (CompoundValue,),
                {'type': self, '__module__': 'zeep.types'})

        return self._value_class(*args, **kwargs)

    @classmethod
    def signature(cls):
        return ', '.join([prop.name for prop in cls.properties()])

    def parse_xmlelement(self, xmlelement):
        instance = self()
        if not self.__metadata__['fields']:
            return instance

        elements = xmlelement.getchildren()
        fields = iter(self.__metadata__['fields'])
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


class String(SimpleType):

    def xmlvalue(self, value):
        return unicode(value)

    def pythonvalue(self, value):
        return unicode(value)


class Boolean(SimpleType):
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
    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return float(value)


class Float(SimpleType):
    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return float(value)


class Decimal(SimpleType):
    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return _Decimal(value)


class Integer(Decimal):

    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return int(value)


class Long(Integer):
    pass


class Element(object):
    def __init__(self, name, type_=None, nsmap=None):
        self.name = name.localname
        self.qname = name
        self.type = type_
        self.nsmap = nsmap or {}

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

        node = etree.SubElement(parent, self.name, nsmap=self.nsmap)
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


default_types = {
    '{http://www.w3.org/2001/XMLSchema}anyType': String,
    '{http://www.w3.org/2001/XMLSchema}anyURI': String,
    '{http://www.w3.org/2001/XMLSchema}ID': String,
    '{http://www.w3.org/2001/XMLSchema}IDREF': String,
    '{http://www.w3.org/2001/XMLSchema}byte': String,
    '{http://www.w3.org/2001/XMLSchema}short': Integer,
    '{http://www.w3.org/2001/XMLSchema}unsignedByte': String,
    '{http://www.w3.org/2001/XMLSchema}unsignedInt': Integer,
    '{http://www.w3.org/2001/XMLSchema}unsignedLong': Long,
    '{http://www.w3.org/2001/XMLSchema}unsignedShort': Integer,
    '{http://www.w3.org/2001/XMLSchema}QName': String,
    '{http://www.w3.org/2001/XMLSchema}string': String,
    '{http://www.w3.org/2001/XMLSchema}float': Float,
    '{http://www.w3.org/2001/XMLSchema}int': Integer,
    '{http://www.w3.org/2001/XMLSchema}long': Long,
    '{http://www.w3.org/2001/XMLSchema}base64Binary': String,
    '{http://www.w3.org/2001/XMLSchema}boolean': Boolean,
    '{http://www.w3.org/2001/XMLSchema}decimal': Decimal,
    '{http://www.w3.org/2001/XMLSchema}dateTime': DateTime,
    '{http://www.w3.org/2001/XMLSchema}double': Double,
}
