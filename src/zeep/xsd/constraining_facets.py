import decimal
import keyword
import re

from zeep.exceptions import ValidationError
from zeep.xsd.const import xsd_ns
from zeep.xsd.types.builtins import (
    AnyURI,
    Base64Binary,
    Boolean,
    Date,
    DateTime,
    Decimal,
    Double,
    Duration,
    Float,
    HexBinary,
    Notation,
    QName,
    String,
    Time,
    gDay,
    gMonth,
    gMonthDay,
    gYear,
    gYearMonth,
)


class tags(object):
    pass


for name in [
    "restriction",
    "length",
    "minLength",
    "maxLength",
    "pattern",
    "enumeration",
    "whiteSpace",
    "maxInclusive",
    "maxExclusive",
    "minInclusive",
    "minExclusive",
    "totalDigits",
    "fractionDigits",
    "assertions",
    "explicitTimezone",
]:
    attr = name if name not in keyword.kwlist else name + "_"
    setattr(tags, attr, xsd_ns(name))


class ConstrainingFacets(object):
    """ConstrainingFacets provides various validation.

    :param node: The XML node
    :type node: lxml.etree._Element

    See references for details.

    References:
        https://www.w3.org/TR/xmlschema11-2/#rf-facets
        https://www.w3.org/TR/xmlschema11-2/#defn-coss
    """

    def __init__(self, node):
        self.length = []
        self.min_length = []
        self.max_length = []
        self.pattern = []
        self.enumeration = []
        self.white_space = []
        self.min_inclusive = []
        self.max_inclusive = []
        self.min_exclusive = []
        self.max_exclusive = []
        self.total_digits = []
        self.fraction_digits = []
        self.assertions = []
        self.explicit_timezone = []

        self._parse_node(node)

    def _parse_node(self, node):
        assert node.tag == tags.restriction

        for child in node.getchildren():
            for k, v in tags.__dict__.items():
                if k.startswith("_"):
                    continue
                if v == child.tag:
                    name = self._to_snake_case(k)
                    values = getattr(self, name)
                    values += child.values()
                    setattr(self, name, values)
                    break

    def _to_snake_case(self, s):
        return re.sub("([A-Z]+)", r"_\1", s).lower()

    def validate(self, typ, value):
        self._validate_length(typ, value)
        self._validate_min_length(typ, value)
        self._validate_max_length(typ, value)
        self._validate_pattern(typ, value)
        self._validate_enumeration(typ, value)
        self._validate_white_space(typ, value)
        self._validate_min_inclusive(typ, value)
        self._validate_max_inclusive(typ, value)
        self._validate_min_exclusive(typ, value)
        self._validate_max_exclusive(typ, value)
        self._validate_total_digits(typ, value)
        self._validate_fraction_digits(typ, value)
        self._validate_assertions(typ, value)
        self._validate_explicit_timezone(typ, value)

    def _validate_length(self, typ, value):
        if isinstance(typ, (String, HexBinary, Base64Binary, AnyURI, QName, Notation)):
            for length in self.length:
                if len(value) != int(length):
                    raise ValidationError("Value cannot satisfy length constraint")

    def _validate_min_length(self, typ, value):
        if isinstance(typ, (String, HexBinary, Base64Binary, AnyURI, QName, Notation)):
            for min_length in self.min_length:
                if len(value) < int(min_length):
                    raise ValidationError("Value cannot satisfy minLength constraint")

    def _validate_max_length(self, typ, value):
        if isinstance(typ, (String, HexBinary, Base64Binary, AnyURI, QName, Notation)):
            for max_length in self.max_length:
                if len(value) > int(max_length):
                    raise ValidationError("Value cannot satisfy maxLength constraint")

    def _validate_pattern(self, typ, value):
        for pattern in self.pattern:
            if not re.match(pattern, str(value)):
                raise ValidationError("Value cannot satisfy pattern constraint")

    def _validate_enumeration(self, typ, value):
        if not isinstance(typ, Boolean):
            if self.enumeration and value not in set(
                [typ.pythonvalue(enum) for enum in self.enumeration]
            ):
                raise ValidationError("Value cannot satisfy enumeration constraint")

    def _validate_white_space(self, typ, value):
        pass  # whiteSpace doesn't specify constraint. It's used for canonicalization.

    def _validate_min_inclusive(self, typ, value):
        if isinstance(typ, (Decimal, Float, Double, Duration, DateTime, Time, Date)):
            for min_inclusive in self.min_inclusive:
                if value < typ.pythonvalue(min_inclusive):
                    raise ValidationError(
                        "Value cannot satisfy minInclusive constraint"
                    )
        elif isinstance(typ, (gYearMonth, gYear, gMonthDay, gDay, gMonth)):
            for min_inclusive in self.min_inclusive:
                if typ.datetimevalue(value) < typ.datetimevalue(typ.pythonvalue(min_inclusive)):
                    raise ValidationError(
                        "Value cannot satisfy minInclusive constraint"
                    )

    def _validate_max_inclusive(self, typ, value):
        if isinstance(typ, (Decimal, Float, Double, Duration, DateTime, Time, Date)):
            for max_inclusive in self.max_inclusive:
                if value > typ.pythonvalue(max_inclusive):
                    raise ValidationError(
                        "Value cannot satisfy maxInclusive constraint"
                    )
        elif isinstance(typ, (gYearMonth, gYear, gMonthDay, gDay, gMonth)):
            for max_inclusive in self.max_inclusive:
                if typ.datetimevalue(value) > typ.datetimevalue(typ.pythonvalue(max_inclusive)):
                    raise ValidationError(
                        "Value cannot satisfy maxInclusive constraint"
                    )

    def _validate_min_exclusive(self, typ, value):
        if isinstance(typ, (Decimal, Float, Double, Duration, DateTime, Time, Date)):
            for min_exclusive in self.min_exclusive:
                if value <= typ.pythonvalue(min_exclusive):
                    raise ValidationError(
                        "Value cannot satisfy minExclusive constraint"
                    )
        elif isinstance(typ, (gYearMonth, gYear, gMonthDay, gDay, gMonth)):
            for min_exclusive in self.min_exclusive:
                if typ.datetimevalue(value) <= typ.datetimevalue(typ.pythonvalue(min_exclusive)):
                    raise ValidationError(
                        "Value cannot satisfy minExclusive constraint"
                    )

    def _validate_max_exclusive(self, typ, value):
        if isinstance(typ, (Decimal, Float, Double, Duration, DateTime, Time, Date)):
            for max_exclusive in self.max_exclusive:
                if value >= typ.pythonvalue(max_exclusive):
                    raise ValidationError(
                        "Value cannot satisfy maxExclusive constraint"
                    )
        elif isinstance(typ, (gYearMonth, gYear, gMonthDay, gDay, gMonth)):
            for max_exclusive in self.max_exclusive:
                if typ.datetimevalue(value) >= typ.datetimevalue(typ.pythonvalue(max_exclusive)):
                    raise ValidationError(
                        "Value cannot satisfy maxExclusive constraint"
                    )

    def _validate_total_digits(self, typ, value):
        if isinstance(typ, Decimal):
            for total_digits in self.total_digits:
                if len(str(int(value))) > int(total_digits):
                    raise ValidationError("Value cannot satisfy totalDigits constraint")

    def _validate_fraction_digits(self, typ, value):
        if isinstance(typ, Decimal):
            for fraction_digits in self.fraction_digits:
                i = str(value).find(".")
                if i == -1:
                    fd = 0
                else:
                    fd = len(str(value)) - 1 - i
                if fd > int(fraction_digits):
                    raise ValidationError(
                        "Value cannot satisfy fractionDigits constraint"
                    )

    def _validate_assertions(self, typ, value):
        pass  # TODO assertions are not supported yet

    def _validate_explicit_timezone(self, typ, value):
        pass  # TODO explicitTimezone are not supported yet
