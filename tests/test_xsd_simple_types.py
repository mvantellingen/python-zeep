from lxml import etree
import isodate
import pytz

from tests.utils import assert_nodes_equal, assert_failure, assert_success, load_xml
from zeep import xsd
from zeep.exceptions import ValidationError

def test_simple_type():
    schema = xsd.Schema(
        load_xml(
            """
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="item">
            <complexType>
              <sequence>
                <element name="something" type="long"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """
        )
    )

    item_cls = schema.get_element("{http://tests.python-zeep.org/}item")
    item = item_cls(something=12345678901234567890)

    node = etree.Element("document")
    item_cls.render(node, item)
    expected = """
        <document>
          <ns0:item xmlns:ns0="http://tests.python-zeep.org/">
            <ns0:something>12345678901234567890</ns0:something>
          </ns0:item>
        </document>
    """
    assert_nodes_equal(expected, node)
    item = item_cls.parse(list(node)[0], schema)
    assert item.something == 12345678901234567890


def test_simple_type_optional():
    schema = xsd.Schema(
        load_xml(
            """
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="item">
            <complexType>
              <sequence>
                <element name="something" type="long" minOccurs="0"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """
        )
    )

    item_cls = schema.get_element("{http://tests.python-zeep.org/}item")
    item = item_cls()
    assert item.something is None

    node = etree.Element("document")
    item_cls.render(node, item)
    expected = """
        <document>
          <ns0:item xmlns:ns0="http://tests.python-zeep.org/"/>
        </document>
    """
    assert_nodes_equal(expected, node)

    item = item_cls.parse(list(node)[0], schema)
    assert item.something is None


def test_restriction_global():
    schema = xsd.Schema(
        load_xml(
            """
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <simpleType name="foo">
            <restriction base="integer">
              <minInclusive value="0"/>
              <maxInclusive value="100"/>
            </restriction>
          </simpleType>
        </schema>
    """
        )
    )

    type_cls = schema.get_type("{http://tests.python-zeep.org/}foo")
    assert type_cls.qname.text == "{http://tests.python-zeep.org/}foo"


def test_restriction_anon():
    schema = xsd.Schema(
        load_xml(
            """
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <element name="something">
            <simpleType>
              <restriction base="integer">
                <minInclusive value="0"/>
                <maxInclusive value="100"/>
              </restriction>
            </simpleType>
          </element>
        </schema>
    """
        )
    )

    element_cls = schema.get_element("{http://tests.python-zeep.org/}something")
    assert element_cls.type.qname == etree.QName(
        "{http://tests.python-zeep.org/}something"
    )

    node = etree.Element("document")
    element_cls.render(node, 75)
    expected = """
        <document>
            <ns0:something xmlns:ns0="http://tests.python-zeep.org/">75</ns0:something>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_simple_type_list():
    schema = xsd.Schema(
        load_xml(
            """
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">

          <simpleType name="values">
            <list itemType="integer"/>
          </simpleType>
          <element name="something" type="tns:values"/>
        </schema>
    """
        )
    )

    element_cls = schema.get_element("{http://tests.python-zeep.org/}something")
    obj = element_cls([1, 2, 3])
    assert obj == [1, 2, 3]

    node = etree.Element("document")
    element_cls.render(node, obj)
    expected = """
        <document>
            <ns0:something xmlns:ns0="http://tests.python-zeep.org/">1 2 3</ns0:something>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_simple_type_list_custom_type():
    schema = xsd.Schema(
        load_xml(
            """
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">

          <simpleType name="CountryNameType">
            <list>
              <simpleType>
                <restriction base="string">
                  <enumeration value="None"/>
                  <enumeration value="AlternateName"/>
                  <enumeration value="City"/>
                  <enumeration value="Code"/>
                  <enumeration value="Country"/>
                </restriction>
              </simpleType>
            </list>
          </simpleType>
          <element name="something" type="tns:CountryNameType"/>
        </schema>
    """
        )
    )

    element_cls = schema.get_element("{http://tests.python-zeep.org/}something")
    obj = element_cls(["Code", "City"])
    assert obj == ["Code", "City"]

    node = etree.Element("document")
    element_cls.render(node, obj)
    expected = """
        <document>
            <ns0:something xmlns:ns0="http://tests.python-zeep.org/">Code City</ns0:something>
        </document>
    """
    assert_nodes_equal(expected, node)


def test_constraints():
    schema = xsd.Schema(
        load_xml(
            """
        <?xml version="1.0"?>
        <schema xmlns="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">

            <simpleType name="length_test">
              <restriction base="string">
                <length value="3" />
              </restriction>
            </simpleType>

            <simpleType name="length_test2">
              <restriction base="string">
                <minLength value="3" />
                <maxLength value="5" />
              </restriction>
            </simpleType>

            <simpleType name="pattern_test">
              <restriction base="string">
                <pattern value="[a-z]" />
              </restriction>
            </simpleType>

            <simpleType name="pattern_test2">
              <restriction base="integer">
                <pattern value="123" />
                <pattern value="321" />
              </restriction>
            </simpleType>

            <simpleType name="enumeration_test">
              <restriction base="string">
                <enumeration value="1" />
                <enumeration value="3" />
              </restriction>
            </simpleType>

            <simpleType name="enumeration_test2">
              <restriction base="integer">
                <enumeration value="1" />
                <enumeration value="3" />
              </restriction>
            </simpleType>

            <simpleType name="inclusive_test">
              <restriction base="integer">
                <minInclusive value="1" />
                <maxInclusive value="4" />
              </restriction>
            </simpleType>

            <simpleType name="inclusive_test2">
              <restriction base="float">
                <minInclusive value="1.1" />
                <maxInclusive value="3.9" />
              </restriction>
            </simpleType>

            <simpleType name="inclusive_test3">
              <restriction base="gYear">
                <minInclusive value="1999Z" />
                <maxInclusive value="2012Z" />
              </restriction>
            </simpleType>

            <simpleType name="exclusive_test">
              <restriction base="integer">
                <minExclusive value="1" />
                <maxExclusive value="4" />
              </restriction>
            </simpleType>

            <simpleType name="exclusive_test2">
              <restriction base="date">
                <minExclusive value="1999-01-01" />
                <maxExclusive value="2005-03-02" />
              </restriction>
            </simpleType>

            <simpleType name="total_digits_test">
              <restriction base="integer">
                <totalDigits value="3" />
              </restriction>
            </simpleType>

            <simpleType name="fraction_digits_test">
              <restriction base="decimal">
                <fractionDigits value="2" />
              </restriction>
            </simpleType>

            <simpleType name="assertions_test">
              <restriction base="integer">
                <assertion test="$value mod 2 = 0" />
                <assertion test="$value > 2" />
              </restriction>
            </simpleType>

            <simpleType name="explicit_timezone_test">
              <restriction base="time">
                <explicitTimezone value="required" />
              </restriction>
            </simpleType>

            <simpleType name="inherit_base">
              <restriction base="integer">
                <enumeration value="4" />
              </restriction>
            </simpleType>

            <simpleType name="inherit_test">
              <restriction base="tns:inherit_base">
                <enumeration value="6" />
              </restriction>
            </simpleType>

            <simpleType name="complex_test">
              <restriction base="integer">
                <totalDigits value="2" />
                <enumeration value="4" />
                <enumeration value="12" />
                <enumeration value="14" />
                <enumeration value="16" />
                <maxInclusive value="15" />
              </restriction>
            </simpleType>
        </schema>
    """
        )
    )

    length_test = schema.get_type("{http://tests.python-zeep.org/}length_test")
    assert_success(lambda: length_test.validate("abc"))
    assert_failure(ValidationError, lambda: length_test.validate("a"))

    length_test2 = schema.get_type("{http://tests.python-zeep.org/}length_test2")
    assert_success(lambda: length_test2.validate("abc"))
    assert_success(lambda: length_test2.validate("abcd"))
    assert_success(lambda: length_test2.validate("abcde"))
    assert_failure(ValidationError, lambda: length_test2.validate("ab"))
    assert_failure(ValidationError, lambda: length_test2.validate("abcdef"))

    pattern_test = schema.get_type("{http://tests.python-zeep.org/}pattern_test")
    assert_success(lambda: pattern_test.validate("abc"))
    assert_failure(ValidationError, lambda: pattern_test.validate("ABC"))

    pattern_test2 = schema.get_type("{http://tests.python-zeep.org/}pattern_test2")
    assert_success(lambda: pattern_test2.validate(123))
    assert_success(lambda: pattern_test2.validate(321))
    assert_failure(ValidationError, lambda: pattern_test2.validate(111))

    enumeration_test = schema.get_type(
        "{http://tests.python-zeep.org/}enumeration_test"
    )
    assert_success(lambda: enumeration_test.validate("1"))
    assert_success(lambda: enumeration_test.validate("3"))
    assert_failure(ValidationError, lambda: enumeration_test.validate("2"))

    enumeration_test2 = schema.get_type(
        "{http://tests.python-zeep.org/}enumeration_test2"
    )
    assert_success(lambda: enumeration_test2.validate(1))
    assert_success(lambda: enumeration_test2.validate(3))
    assert_failure(ValidationError, lambda: enumeration_test2.validate(2))

    inclusive_test = schema.get_type("{http://tests.python-zeep.org/}inclusive_test")
    assert_success(lambda: inclusive_test.validate(1))
    assert_success(lambda: inclusive_test.validate(2))
    assert_success(lambda: inclusive_test.validate(3))
    assert_success(lambda: inclusive_test.validate(4))
    assert_failure(ValidationError, lambda: inclusive_test.validate(0))
    assert_failure(ValidationError, lambda: inclusive_test.validate(5))

    inclusive_test2 = schema.get_type(
        "{http://tests.python-zeep.org/}inclusive_test2"
    )
    assert_success(lambda: inclusive_test2.validate(1.2))
    assert_success(lambda: inclusive_test2.validate(3))
    assert_failure(ValidationError, lambda: inclusive_test2.validate(1))
    assert_failure(ValidationError, lambda: inclusive_test2.validate(4))

    inclusive_test3 = schema.get_type(
        "{http://tests.python-zeep.org/}inclusive_test3"
    )
    assert_success(lambda: inclusive_test3.validate((2000, pytz.UTC)))
    assert_failure(ValidationError, lambda: inclusive_test3.validate((2020, pytz.UTC)))

    exclusive_test = schema.get_type("{http://tests.python-zeep.org/}exclusive_test")
    assert_success(lambda: exclusive_test.validate(2))
    assert_success(lambda: exclusive_test.validate(3))
    assert_failure(ValidationError, lambda: exclusive_test.validate(1))
    assert_failure(ValidationError, lambda: exclusive_test.validate(4))

    exclusive_test2 = schema.get_type("{http://tests.python-zeep.org/}exclusive_test2")
    assert_success(lambda: exclusive_test2.validate(isodate.parse_date("1999-01-02")))
    assert_failure(ValidationError, lambda: exclusive_test2.validate(isodate.parse_date("1998-01-02")))

    total_digits_test = schema.get_type(
        "{http://tests.python-zeep.org/}total_digits_test"
    )
    assert_success(lambda: total_digits_test.validate(12))
    assert_success(lambda: total_digits_test.validate(123))
    assert_failure(ValidationError, lambda: total_digits_test.validate(1234))

    fraction_digits_test = schema.get_type(
        "{http://tests.python-zeep.org/}fraction_digits_test"
    )
    assert_success(lambda: fraction_digits_test.validate(12.3))
    assert_success(lambda: fraction_digits_test.validate(12.34))
    assert_failure(ValidationError, lambda: fraction_digits_test.validate(12.345))

    assertions_test = schema.get_type(
        "{http://tests.python-zeep.org/}assertions_test"
    )
    assert_success(lambda: assertions_test.validate(4))
    assert_failure(ValidationError, lambda: assertions_test.validate(3))
    assert_failure(ValidationError, lambda: assertions_test.validate(2))

    explicit_timezone_test = schema.get_type(
        "{http://tests.python-zeep.org/}explicit_timezone_test"
    )
    assert_success(lambda: explicit_timezone_test.validate(isodate.parse_time("19:00Z")))
    assert_failure(ValidationError, lambda: explicit_timezone_test.validate(isodate.parse_time("19:00")))

    # inherit_test = schema.get_type("{http://tests.python-zeep.org/}inherit_test")
    # assert_success(lambda: inherit_test.validate(4))
    # assert_success(lambda: inherit_test.validate(6))
    # assert_failure(ValidationError, lambda: inherit_test.validate(8))

    complex_test = schema.get_type("{http://tests.python-zeep.org/}complex_test")
    assert_success(lambda: complex_test.validate(4))
    assert_success(lambda: complex_test.validate(14))
    assert_failure(ValidationError, lambda: complex_test.validate(16))
