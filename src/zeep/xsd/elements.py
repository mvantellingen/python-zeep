from lxml import etree


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
