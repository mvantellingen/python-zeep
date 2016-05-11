"""
    Primitive datatypes
     - string
     - boolean
     - decimal
     - float
     - double
     - duration
     - dateTime
     - time
     - date
     - gYearMonth
     - gYear
     - gMonthDay
     - gDay
     - gMonth
     - hexBinary
     - base64Binary
     - anyURI
     - QName
     - NOTATION

    Derived datatypes
     - normalizedString
     - token
     - language
     - NMTOKEN
     - NMTOKENS
     - Name
     - NCName
     - ID
     - IDREF
     - IDREFS
     - ENTITY
     - ENTITIES
     - integer
     - nonPositiveInteger
     - negativeInteger
     - long
     - int
     - short
     - byte
     - nonNegativeInteger
     - unsignedLong
     - unsignedInt
     - unsignedShort
     - unsignedByte
     - positiveInteger


"""
from __future__ import division

import base64
import math
import re
from decimal import Decimal as _Decimal

import isodate
import pytz
import six

from zeep.xsd.types import SimpleType


class ParseError(ValueError):
    pass


##
# Primitive types

class String(SimpleType):
    name = 'xsd:string'

    def xmlvalue(self, value):
        return six.text_type(value)

    def pythonvalue(self, value):
        return value


class Boolean(SimpleType):
    name = 'xsd:boolean'

    def xmlvalue(self, value):
        return 'true' if value else 'false'

    def pythonvalue(self, value):
        """Return True if the 'true' or '1'. 'false' and '0' are legal false
        values, but we consider everything not true as false.

        """
        return value in ('true', '1')


class Decimal(SimpleType):
    name = 'xsd:decimal'

    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return _Decimal(value)


class Float(SimpleType):
    name = 'xsd:float'

    def xmlvalue(self, value):
        return str(value).upper()

    def pythonvalue(self, value):
        return float(value)


class Double(SimpleType):
    name = 'xsd:double'

    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return float(value)


class Duration(SimpleType):
    name = 'xsd:duration'

    def xmlvalue(self, value):
        return isodate.duration_isoformat(value)

    def pythonvalue(self, value):
        return isodate.parse_duration(value)


class DateTime(SimpleType):
    name = 'xsd:dateTime'

    def xmlvalue(self, value):
        return isodate.isostrf.strftime(value, '%Y-%m-%dT%H:%M:%S%Z')

    def pythonvalue(self, value):
        return isodate.parse_datetime(value)


class Time(SimpleType):
    name = 'xsd:time'

    def xmlvalue(self, value):
        return isodate.isostrf.strftime(value, '%H:%M:%S%Z')

    def pythonvalue(self, value):
        return isodate.parse_time(value)


class Date(SimpleType):
    name = 'xsd:date'

    def xmlvalue(self, value):
        return isodate.isostrf.strftime(value, '%Y-%m-%d')

    def pythonvalue(self, value):
        return isodate.parse_date(value)


class gYearMonth(SimpleType):
    """gYearMonth represents a specific gregorian month in a specific gregorian
    year.

    Lexical representation: CCYY-MM

    """
    name = 'xsd:gYearMonth'
    _pattern = re.compile(
        r'^(?P<year>-?\d{4,})-(?P<month>\d\d)(?P<timezone>Z|[-+]\d\d:?\d\d)?$')

    def xmlvalue(self, value):
        year, month, tzinfo = value
        return '%04d-%02d%s' % (year, month, _unparse_timezone(tzinfo))

    def pythonvalue(self, value):
        match = self._pattern.match(value)
        if not match:
            raise ParseError()
        group = match.groupdict()
        return (
            int(group['year']), int(group['month']),
            _parse_timezone(group['timezone']))


class gYear(SimpleType):
    """gYear represents a gregorian calendar year.

    Lexical representation: CCYY

    """
    name = 'xsd:gYear'
    _pattern = re.compile(r'^(?P<year>-?\d{4,})(?P<timezone>Z|[-+]\d\d:?\d\d)?$')

    def xmlvalue(self, value):
        year, tzinfo = value
        return '%04d%s' % (year, _unparse_timezone(tzinfo))

    def pythonvalue(self, value):
        match = self._pattern.match(value)
        if not match:
            raise ParseError()
        group = match.groupdict()
        return (int(group['year']), _parse_timezone(group['timezone']))


class gMonthDay(SimpleType):
    """gMonthDay is a gregorian date that recurs, specifically a day of the
    year such as the third of May.

    Lexical representation: --MM-DD

    """

    name = 'xsd:gMonthDay'
    _pattern = re.compile(
        r'^--(?P<month>\d\d)-(?P<day>\d\d)(?P<timezone>Z|[-+]\d\d:?\d\d)?$')

    def xmlvalue(self, value):
        month, day, tzinfo = value
        return '--%02d-%02d%s' % (month, day, _unparse_timezone(tzinfo))

    def pythonvalue(self, value):
        match = self._pattern.match(value)
        if not match:
            raise ParseError()

        group = match.groupdict()
        return (
            int(group['month']), int(group['day']),
            _parse_timezone(group['timezone']))


class gDay(SimpleType):
    """gDay is a gregorian day that recurs, specifically a day of the month
    such as the 5th of the month

    Lexical representation: ---DD

    """
    name = 'xsd:gDay'
    _pattern = re.compile(r'^---(?P<day>\d\d)(?P<timezone>Z|[-+]\d\d:?\d\d)?$')

    def xmlvalue(self, value):
        day, tzinfo = value
        return '---%02d%s' % (day, _unparse_timezone(tzinfo))

    def pythonvalue(self, value):
        match = self._pattern.match(value)
        if not match:
            raise ParseError()
        group = match.groupdict()
        return (int(group['day']), _parse_timezone(group['timezone']))


class gMonth(SimpleType):
    """gMonth is a gregorian month that recurs every year.

    Lexical representation: --MM

    """
    name = 'xsd:gMonth'
    _pattern = re.compile(r'^--(?P<month>\d\d)(?P<timezone>Z|[-+]\d\d:?\d\d)?$')

    def xmlvalue(self, value):
        month, tzinfo = value
        return '--%d%s' % (month, _unparse_timezone(tzinfo))

    def pythonvalue(self, value):
        match = self._pattern.match(value)
        if not match:
            raise ParseError()
        group = match.groupdict()
        return (int(group['month']), _parse_timezone(group['timezone']))


class HexBinary(SimpleType):
    name = 'xsd:hexBinary'

    def xmlvalue(self, value):
        return value

    def pythonvalue(self, value):
        return value


class Base64Binary(SimpleType):
    name = 'xsd:base64Binary'

    def xmlvalue(self, value):
        return base64.b64encode(value)

    def pythonvalue(self, value):
        return base64.b64decode(value)


class AnyURI(SimpleType):
    name = 'xsd:anyURI'

    def xmlvalue(self, value):
        return value

    def pythonvalue(self, value):
        return value


class QName(SimpleType):
    name = 'xsd:QName'


class Notation(SimpleType):
    name = 'xsd:NOTATION'


##
# Derived datatypes

class NormalizedString(String):
    name = 'xsd:normalizedString'


class Token(NormalizedString):
    name = 'xsd:token'


class Language(Token):
    name = 'xsd:language'


class NmToken(Token):
    name = 'xsd:NMTOKEN'


class NmTokens(NmToken):
    name = 'xsd:NMTOKENS'


class Name(Token):
    name = 'xsd:Name'


class NCName(Name):
    name = 'xsd:NCName'


class ID(NCName):
    name = 'xsd:ID'


class IDREF(NCName):
    name = 'xsd:IDREF'


class IDREFS(IDREF):
    name = 'xsd:IDREFS'


class Entity(NCName):
    name = 'xsd:ENTITY'


class Entities(Entity):
    name = 'xsd:ENTITIES'


class Integer(Decimal):
    name = 'xsd:integer'

    def xmlvalue(self, value):
        return str(value)

    def pythonvalue(self, value):
        return int(value)


class NonPositiveInteger(Integer):
    name = 'xsd:nonPositiveInteger'


class NegativeInteger(Integer):
    name = 'xsd:negativeInteger'


class Long(Integer):
    name = 'xsd:long'

    def pythonvalue(self, value):
        return long(value) if six.PY2 else int(value)


class Int(Long):
    name = 'xsd:int'


class Short(Int):
    name = 'xsd:short'


class Byte(Short):
    """A signed 8-bit integer"""
    name = 'xsd:byte'


class NonNegativeInteger(Integer):
    name = 'xsd:nonNegativeInteger'


class UnsignedLong(NonNegativeInteger):
    name = 'xsd:unsignedLong'


class UnsignedInt(UnsignedLong):
    name = 'xsd:unsignedInt'


class UnsignedShort(UnsignedInt):
    name = 'xsd:unsignedShort'


class UnsignedByte(UnsignedShort):
    name = 'xsd:unsignedByte'


class PositiveInteger(NonNegativeInteger):
    name = 'xsd:positiveInteger'


##
# Other

class AnyType(SimpleType):
    name = 'xsd:anyType'

    def xmlvalue(self, value):
        return value

    def pythonvalue(self, value):
        return value


def _parse_timezone(val):
    """Return a pytz.tzinfo object"""
    if not val:
        return

    if val == 'Z' or val == '+00:00':
        return pytz.utc

    negative = val.startswith('-')
    minutes = int(val[-2:])
    minutes += int(val[1:3]) * 60

    if negative:
        minutes = 0 - minutes
    return pytz.FixedOffset(minutes)


def _unparse_timezone(tzinfo):
    if not tzinfo:
        return ''

    if tzinfo == pytz.utc:
        return 'Z'

    hours = math.floor(tzinfo._minutes / 60)
    minutes = tzinfo._minutes % 60

    if hours > 0:
        return '+%02d:%02d' % (hours, minutes)
    return '-%02d:%02d' % (abs(hours), minutes)


default_types = {

    # Primitive
    '{http://www.w3.org/2001/XMLSchema}string': String(),
    '{http://www.w3.org/2001/XMLSchema}boolean': Boolean(),
    '{http://www.w3.org/2001/XMLSchema}decimal': Decimal(),
    '{http://www.w3.org/2001/XMLSchema}float': Float(),
    '{http://www.w3.org/2001/XMLSchema}double': Double(),
    '{http://www.w3.org/2001/XMLSchema}duration': Duration(),
    '{http://www.w3.org/2001/XMLSchema}dateTime': DateTime(),
    '{http://www.w3.org/2001/XMLSchema}time': Time(),
    '{http://www.w3.org/2001/XMLSchema}date': Date(),
    '{http://www.w3.org/2001/XMLSchema}gYearMonth': gYearMonth(),
    '{http://www.w3.org/2001/XMLSchema}gYear': gYear(),
    '{http://www.w3.org/2001/XMLSchema}gMonthDay': gMonthDay(),
    '{http://www.w3.org/2001/XMLSchema}gDay': gDay(),
    '{http://www.w3.org/2001/XMLSchema}gMonth': gMonth(),
    '{http://www.w3.org/2001/XMLSchema}hexBinary': HexBinary(),
    '{http://www.w3.org/2001/XMLSchema}base64Binary': Base64Binary(),
    '{http://www.w3.org/2001/XMLSchema}anyURI': AnyURI(),
    '{http://www.w3.org/2001/XMLSchema}QName': QName(),
    '{http://www.w3.org/2001/XMLSchema}NOTATION': Notation(),

    # Derived
    '{http://www.w3.org/2001/XMLSchema}normalizedString': ID(),
    '{http://www.w3.org/2001/XMLSchema}token': ID(),
    '{http://www.w3.org/2001/XMLSchema}language': ID(),
    '{http://www.w3.org/2001/XMLSchema}NMTOKEN': ID(),
    '{http://www.w3.org/2001/XMLSchema}NMTOKENS': ID(),
    '{http://www.w3.org/2001/XMLSchema}Name': ID(),
    '{http://www.w3.org/2001/XMLSchema}NCName': ID(),
    '{http://www.w3.org/2001/XMLSchema}ID': ID(),
    '{http://www.w3.org/2001/XMLSchema}IDREF': IDREF(),
    '{http://www.w3.org/2001/XMLSchema}IDREFS': IDREFS(),
    '{http://www.w3.org/2001/XMLSchema}ENTITY': Entity(),
    '{http://www.w3.org/2001/XMLSchema}ENTITIES': Entities(),
    '{http://www.w3.org/2001/XMLSchema}integer': Integer(),
    '{http://www.w3.org/2001/XMLSchema}nonPositiveInteger': NonPositiveInteger(),  # noqa
    '{http://www.w3.org/2001/XMLSchema}negativeInteger': NegativeInteger(),
    '{http://www.w3.org/2001/XMLSchema}long': Long(),
    '{http://www.w3.org/2001/XMLSchema}int': Int(),
    '{http://www.w3.org/2001/XMLSchema}short': Short(),
    '{http://www.w3.org/2001/XMLSchema}byte': Byte(),
    '{http://www.w3.org/2001/XMLSchema}nonNegativeInteger': NonNegativeInteger(),  # noqa
    '{http://www.w3.org/2001/XMLSchema}unsignedByte': String(),
    '{http://www.w3.org/2001/XMLSchema}unsignedInt': UnsignedInt(),
    '{http://www.w3.org/2001/XMLSchema}unsignedLong': UnsignedLong(),
    '{http://www.w3.org/2001/XMLSchema}unsignedShort': UnsignedShort(),
    '{http://www.w3.org/2001/XMLSchema}positiveInteger': PositiveInteger(),

    # Other
    '{http://www.w3.org/2001/XMLSchema}anyType': AnyType(),
}
