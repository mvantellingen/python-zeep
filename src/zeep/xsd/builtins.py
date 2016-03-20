from decimal import Decimal as _Decimal

from zeep.xsd.types import SimpleType


class AnyType(SimpleType):
    name = 'xsd:anyType'

    def xmlvalue(self, value):
        return value

    def pythonvalue(self, value):
        return value


class AnyURI(SimpleType):
    name = 'xsd:anyURI'

    def xmlvalue(self, value):
        return value

    def pythonvalue(self, value):
        return value


class String(SimpleType):
    name = 'xsd:string'

    def xmlvalue(self, value):
        return value

    def pythonvalue(self, value):
        return value


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
    name = 'xsd:dateTime'

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


class Long(Integer):
    name = 'xsd:long'

    def pythonvalue(self, value):
        return long(value)


class Short(Integer):
    name = 'xsd:short'


class UnsignedInt(Integer):
    name = 'xsd:UnsignedInt'


class UnsignedLong(Long):
    name = 'xsd:UnsignedLong'


class UnsignedShort(Short):
    name = 'xsd:UnsignedShort'



default_types = {
    '{http://www.w3.org/2001/XMLSchema}ID': ID(),
    '{http://www.w3.org/2001/XMLSchema}IDREF': IDREF(),
    '{http://www.w3.org/2001/XMLSchema}QName': QName(),
    '{http://www.w3.org/2001/XMLSchema}anyType': AnyType(),
    '{http://www.w3.org/2001/XMLSchema}anyURI': AnyURI(),
    '{http://www.w3.org/2001/XMLSchema}base64Binary': Base64Binary(),
    '{http://www.w3.org/2001/XMLSchema}boolean': Boolean(),
    '{http://www.w3.org/2001/XMLSchema}byte': Byte(),
    '{http://www.w3.org/2001/XMLSchema}dateTime': DateTime(),
    '{http://www.w3.org/2001/XMLSchema}decimal': Decimal(),
    '{http://www.w3.org/2001/XMLSchema}double': Double(),
    '{http://www.w3.org/2001/XMLSchema}float': Float(),
    '{http://www.w3.org/2001/XMLSchema}int': Integer(),
    '{http://www.w3.org/2001/XMLSchema}long': Long(),
    '{http://www.w3.org/2001/XMLSchema}short': Short(),
    '{http://www.w3.org/2001/XMLSchema}string': String(),
    '{http://www.w3.org/2001/XMLSchema}unsignedByte': String(),
    '{http://www.w3.org/2001/XMLSchema}unsignedInt': UnsignedInt(),
    '{http://www.w3.org/2001/XMLSchema}unsignedLong': UnsignedLong(),
    '{http://www.w3.org/2001/XMLSchema}unsignedShort': UnsignedShort(),
}
