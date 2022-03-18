from collections import namedtuple
from enum import Enum
import re
from typing import Any, List, Optional

from lxml import etree

from zeep.xsd.const import xsd_ns

Whitespace = Enum('Whitespace', ('preserve', 'replace', 'collapse'))


class Facets(namedtuple('Facets', (
    'enumeration',
    'fraction_digits',
    'length',
    'max_exclusive',
    'max_inclusive',
    'max_length',
    'min_exclusive',
    'min_inclusive',
    'min_length',
    'patterns',
    'total_digits',
    'whitespace',
))):
    def __new__(
            cls,
            enumeration: Optional[List[Any]] = None,
            fraction_digits: Optional[int] = None,
            length: Optional[int] = None,
            max_exclusive: Optional[Any] = None,
            max_inclusive: Optional[Any] = None,
            max_length: Optional[int] = None,
            min_exclusive: Optional[Any] = None,
            min_inclusive: Optional[Any] = None,
            min_length: Optional[int] = None,
            patterns: Optional[List[re.Pattern]] = None,
            total_digits: Optional[int] = None,
            whitespace: Optional[Whitespace] = None):
        kwargs = locals()
        del kwargs['cls']
        del kwargs['__class__']
        return super().__new__(cls, **kwargs)

    @classmethod
    def parse_xml(cls, restriction_elem: etree._Element):
        kwargs = {}
        enumeration = []
        patterns = []
        for facet in restriction_elem:
            if facet.tag == xsd_ns('enumeration'):
                enumeration.append(facet.get('value'))
            elif facet.tag == xsd_ns('fractionDigits'):
                kwargs['fraction_digits'] = int(facet.get('value'))
            elif facet.tag == xsd_ns('length'):
                kwargs['length'] = int(facet.get('value'))
            elif facet.tag == xsd_ns('maxExclusive'):
                kwargs['max_exclusive'] = facet.get('value')
            elif facet.tag == xsd_ns('maxInclusive'):
                kwargs['max_inclusive'] = facet.get('value')
            elif facet.tag == xsd_ns('maxLength'):
                kwargs['max_length'] = int(facet.get('value'))
            elif facet.tag == xsd_ns('minExclusive'):
                kwargs['min_exclusive'] = facet.get('value')
            elif facet.tag == xsd_ns('minInclusive'):
                kwargs['min_inclusive'] = facet.get('value')
            elif facet.tag == xsd_ns('minLength'):
                kwargs['min_length'] = int(facet.get('value'))
            elif facet.tag == xsd_ns('pattern'):
                patterns.append(re.compile(facet.get('value')))
            elif facet.tag == xsd_ns('totalDigits'):
                kwargs['total_digits'] = int(facet.get('value'))
            elif facet.tag == xsd_ns('whiteSpace'):
                kwargs['whitesapce'] = Whitespace[facet.get('value')]

        if enumeration:
            kwargs['enumeration'] = enumeration
        if patterns:
            kwargs['patterns'] = patterns
        return cls(**kwargs)

    def parse_values(self, xsd_type):
        """Convert captured string values to their native Python types.
        """
        def map_opt(f, v):
            return None if v is None else f(v)

        def go(v):
            return map_opt(xsd_type.pythonvalue, v)

        return self._replace(
            enumeration=map_opt(lambda es: [go(e) for e in es], self.enumeration),
            max_exclusive=go(self.max_exclusive),
            max_inclusive=go(self.max_inclusive),
            min_exclusive=go(self.min_exclusive),
            min_inclusive=go(self.min_inclusive),
        )
