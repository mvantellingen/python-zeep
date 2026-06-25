from tests.utils import load_xml

from zeep import xsd


def test_parse_xml():
    schema_doc = load_xml(
        b"""
        <?xml version="1.0" encoding="utf-8"?>
        <xsd:schema xmlns:tns="http://tests.python-zeep.org/attr"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          elementFormDefault="qualified"
          targetNamespace="http://tests.python-zeep.org/facets">
          <xsd:simpleType name="SomeType">
            <xsd:restriction base="xsd:float">
              <xsd:enumeration value="42.0"/>
              <xsd:enumeration value="42.9"/>
              <xsd:minInclusive value="42.0"/>
              <xsd:maxExclusive value="43.0"/>
            </xsd:restriction>
          </xsd:simpleType>
        </xsd:schema>
    """
    )
    schema = xsd.Schema(schema_doc)
    ty = schema.get_type('{http://tests.python-zeep.org/facets}SomeType')
    assert ty.facets.enumeration == [42.0, 42.9]
    assert ty.facets.min_inclusive == 42.0
    assert ty.facets.max_exclusive == 43.0
