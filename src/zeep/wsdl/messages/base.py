from collections import namedtuple

from zeep import xsd

SerializedMessage = namedtuple(
    'SerializedMessage', ['path', 'headers', 'content'])


class ConcreteMessage(object):
    """Represents the wsdl:binding -> wsdl:operation -> input/ouput node"""
    def __init__(self, wsdl, name, operation):
        assert wsdl
        assert operation

        self.wsdl = wsdl
        self.namespace = {}
        self.operation = operation
        self.name = name

    def serialize(self, *args, **kwargs):
        raise NotImplementedError()

    def deserialize(self, node):
        raise NotImplementedError()

    def signature(self, as_output=False):
        if not self.body:
            return None

        if as_output:
            if isinstance(self.body.type, xsd.ComplexType):
                try:
                    if len(self.body.type.elements) == 1:
                        return self.body.type.elements[0][1].type.signature(
                            schema=self.wsdl.types, standalone=False)
                except AttributeError:
                    return None

            return self.body.type.signature(schema=self.wsdl.types, standalone=False)

        parts = [self.body.type.signature(schema=self.wsdl.types, standalone=False)]
        if getattr(self, 'header', None):
            parts.append('_soapheaders={%s}' % self.header.signature(
                schema=self.wsdl.types), standalone=False)
        return ', '.join(part for part in parts if part)

    @classmethod
    def parse(cls, wsdl, xmlelement, abstract_message, operation):
        raise NotImplementedError()
