from zeep.xsd.utils import create_prefixed_name


class Type(object):

    def __init__(self, qname=None, is_global=False):
        self.qname = qname
        self.name = qname.localname if qname else None
        self._resolved = False
        self.is_global = is_global

    def get_prefixed_name(self, schema):
        return create_prefixed_name(self.qname, schema)

    def accept(self, value):
        raise NotImplementedError

    def validate(self, value, required=False):
        return

    def parse_kwargs(self, kwargs, name, available_kwargs):
        value = None
        name = name or self.name

        if name in available_kwargs:
            value = kwargs[name]
            available_kwargs.remove(name)
            return {name: value}
        return {}

    def parse_xmlelement(self, xmlelement, schema=None, allow_none=True,
                         context=None):
        raise NotImplementedError(
            '%s.parse_xmlelement() is not implemented' % self.__class__.__name__)

    def parsexml(self, xml, schema=None):
        raise NotImplementedError

    def render(self, parent, value, xsd_type=None, render_path=None):
        raise NotImplementedError(
            '%s.render() is not implemented' % self.__class__.__name__)

    def resolve(self):
        raise NotImplementedError(
            '%s.resolve() is not implemented' % self.__class__.__name__)

    def extend(self, child):
        raise NotImplementedError(
            '%s.extend() is not implemented' % self.__class__.__name__)

    def restrict(self, child):
        raise NotImplementedError(
            '%s.restrict() is not implemented' % self.__class__.__name__)

    @property
    def attributes(self):
        return []

    @classmethod
    def signature(cls, schema=None, standalone=True):
        return ''


class UnresolvedType(Type):
    def __init__(self, qname, schema):
        self.qname = qname
        assert self.qname.text != 'None'
        self.schema = schema

    def __repr__(self):
        return '<%s(qname=%r)>' % (self.__class__.__name__, self.qname.text)

    def render(self, parent, value, xsd_type=None, render_path=None):
        raise RuntimeError(
            "Unable to render unresolved type %s. This is probably a bug." % (
                self.qname))

    def resolve(self):
        retval = self.schema.get_type(self.qname)
        return retval.resolve()


class UnresolvedCustomType(Type):

    def __init__(self, qname, base_type, schema):
        assert qname is not None
        self.qname = qname
        self.name = str(qname.localname)
        self.schema = schema
        self.base_type = base_type

    def __repr__(self):
        return '<%s(qname=%r, base_type=%r)>' % (
            self.__class__.__name__, self.qname.text, self.base_type)

    def resolve(self):
        base = self.base_type
        base = base.resolve()

        cls_attributes = {
            '__module__': 'zeep.xsd.dynamic_types',
        }

        from zeep.xsd.types.collection import UnionType  # FIXME
        from zeep.xsd.types.simple import AnySimpleType  # FIXME

        if issubclass(base.__class__, UnionType):
            xsd_type = type(self.name, (base.__class__,), cls_attributes)
            return xsd_type(base.item_types)

        elif issubclass(base.__class__, AnySimpleType):
            xsd_type = type(self.name, (base.__class__,), cls_attributes)
            return xsd_type(self.qname)

        else:
            xsd_type = type(self.name, (base.base_class,), cls_attributes)
            return xsd_type(self.qname)
