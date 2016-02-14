import six
from lxml import etree


class Type(object):
    def accept(self, value):
        raise NotImplementedError

    def parse_xmlelement(self, xmlelement):
        raise NotImplementedError

    def parsexml(self, xml):
        raise NotImplementedError

    def render(self, parent, value):
        raise NotImplementedError


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
        cls = type(self.__class__.__name__, (CompoundValue,), {'type': self})
        return cls(**kwargs)

    def parse_xmlelement(self, xmlelement):
        instance = self()

        elements = xmlelement.getchildren()

        fields = iter(self.__metadata__['fields'])
        field = next(fields, None)

        for element in elements:
            if field.name != element.tag:
                field = next(fields, None)

            if field.name != element.tag:
                # XXX Element might be optional
                raise ValueError("Unexpected element")

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


class Decimal(SimpleType):
    pass


class Integer(Decimal):

    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return int(value)


class Element(object):
    def __init__(self, name, type_=None, nsmap=None):
        self.name = name
        self.type = type_
        self.nsmap = nsmap or {}

    def __repr__(self):
        return '<%s(name=%r, type=%r)>' % (self.__class__.__name__, self.name, self.type)

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


class CompoundValueMeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(CompoundValueMeta, cls).__new__

        # Also ensure initialization is only performed for subclasses of Model
        # (excluding Model class itself).
        parents = [b for b in bases if isinstance(b, CompoundValueMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        new_class = super_new(cls, name, bases, {'__module__': 'sopje'})
        for key, value in attrs.items():
            setattr(new_class, key, value)
        return new_class


class CompoundValue(six.with_metaclass(CompoundValueMeta)):

    def __init__(self, *args, **kwargs):
        properties = {
            prop.name: prop() for prop in self.type.properties()
        }

        for key, value in properties.iteritems():
            setattr(self, key, value)

        for key, value in kwargs.items():
            if key not in properties:
                raise TypeError(
                    "__init__() got an unexpected keyword argument %r" % key)
            setattr(self, key, value)


default_types = {
    '{http://www.w3.org/2001/XMLSchema}string': String,
    '{http://www.w3.org/2001/XMLSchema}float': String,
    '{http://www.w3.org/2001/XMLSchema}int': String,
    '{http://www.w3.org/2001/XMLSchema}long': String,
    '{http://www.w3.org/2001/XMLSchema}base64Binary': String,
    '{http://www.w3.org/2001/XMLSchema}boolean': String,
    '{http://www.w3.org/2001/XMLSchema}decimal': String,
    '{http://www.w3.org/2001/XMLSchema}dateTime': String,
    '{http://www.w3.org/2001/XMLSchema}double': String,
}
