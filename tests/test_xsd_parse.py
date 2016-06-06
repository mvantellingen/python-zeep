from lxml import etree

from tests.utils import load_xml
from zeep import xsd


def test_parse_basic():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            children=[
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.String()),
            ]
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2 == 'bar'


def test_parse_basic_with_attrs():
    custom_element = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            children=[
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.String()),
                xsd.Attribute(
                    etree.QName('http://tests.python-zeep.org/', 'attr_1'),
                    xsd.String()),
            ]
        ))
    expected = etree.fromstring("""
        <ns0:authentication xmlns:ns0="http://tests.python-zeep.org/" attr_1="x">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:authentication>
    """)
    obj = custom_element.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2 == 'bar'
    assert obj.attr_1 == 'x'


def test_parse_with_optional():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'container'),
        xsd.ComplexType(
            children=[
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.ComplexType(
                        children=[
                            xsd.Element(
                                etree.QName('http://tests.python-zeep.org/', 'item_2_1'),
                                xsd.String(),
                                nillable=True)
                        ]
                    )
                ),
                xsd.ListElement(
                    etree.QName('http://tests.python-zeep.org/', 'item_3'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_4'),
                    xsd.String(),
                    min_occurs=0),
            ]
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>1</ns0:item_1>
          <ns0:item_2/>
          <ns0:item_3>3</ns0:item_3>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == '1'
    assert obj.item_2 is None
    assert obj.item_3 == ['3']
    assert obj.item_4 is None


def test_parse_regression():
    schema_doc = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <xsd:schema xmlns:tns="http://tests.python-zeep.org/attr"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          elementFormDefault="qualified"
          targetNamespace="http://tests.python-zeep.org/attr">
          <xsd:complexType name="Result">
            <xsd:attribute name="id" type="xsd:int" use="required"/>
          </xsd:complexType>
          <xsd:element name="Response">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element minOccurs="0" maxOccurs="1" name="Result" type="tns:Result"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """)

    response_doc = load_xml(b"""
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
          <s:Body xmlns:xsd="http://www.w3.org/2001/XMLSchema">
            <Response xmlns="http://tests.python-zeep.org/attr">
                <Result id="2"/>
            </Response>
          </s:Body>
        </s:Envelope>
    """)

    schema = xsd.Schema(schema_doc)
    elm = schema.get_element('{http://tests.python-zeep.org/attr}Response')

    node = response_doc.xpath(
        '//ns0:Response', namespaces={
            'xsd': 'http://www.w3.org/2001/XMLSchema',
            'ns0': 'http://tests.python-zeep.org/attr',
        })
    response = elm.parse(node[0], None)
    assert response.Result.id == 2


def test_parse_anytype():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'container'),
        xsd.ComplexType(
            children=[
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.AnyType()),
            ]
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'


def test_parse_anytype_obj():
    value_type = xsd.ComplexType(
        children=[
            xsd.Element(
                '{http://tests.python-zeep.org/}value',
                xsd.Integer()),
        ]
    )

    schema = xsd.Schema()
    schema.register_type('{http://tests.python-zeep.org/}something', value_type)

    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'container'),
        xsd.ComplexType(
            children=[
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.AnyType()),
            ]
        ))
    expected = etree.fromstring("""
        <ns0:container
            xmlns:ns0="http://tests.python-zeep.org/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <ns0:item_1 xsi:type="ns0:something">
            <ns0:value>100</ns0:value>
          </ns0:item_1>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, schema)
    assert obj.item_1.value == 100


def test_parse_anytype_regression_17():
    schema_doc = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <schema
            xmlns="http://www.w3.org/2001/XMLSchema"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/tst"
            elementFormDefault="qualified"
            targetNamespace="http://tests.python-zeep.org/tst">
          <complexType name="CustomField">
            <sequence>
              <element name="parentItemURI" type="xsd:string"/>
              <element name="key" type="xsd:string"/>
              <element name="value" nillable="true"/>
            </sequence>
          </complexType>
          <complexType name="Text">
            <sequence>
              <element name="type" type="xsd:string"/>
              <element name="content" type="xsd:string"/>
              <element name="contentLossy" type="xsd:boolean"/>
            </sequence>
          </complexType>

          <element name="getCustomFieldResponse">
            <complexType>
              <sequence>
                <element name="getCustomFieldReturn" type="tns:CustomField"/>
              </sequence>
            </complexType>
          </element>
        </schema>
    """)

    xml = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <tst:getCustomFieldResponse
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:tst="http://tests.python-zeep.org/tst">
          <tst:getCustomFieldReturn>
            <tst:parentItemURI>blabla</tst:parentItemURI>
            <tst:key>solution</tst:key>
            <tst:value xsi:type="tst:Text">
              <tst:type xsi:type="xsd:string">text/html</tst:type>
              <tst:content xsi:type="xsd:string">Test Solution</tst:content>
              <tst:contentLossy xsi:type="xsd:boolean">false</tst:contentLossy>
            </tst:value>
          </tst:getCustomFieldReturn>
        </tst:getCustomFieldResponse>
    """)

    schema = xsd.Schema(schema_doc)
    elm = schema.get_element(
        '{http://tests.python-zeep.org/tst}getCustomFieldResponse'
    )
    result = elm.parse(xml, schema)
    assert result.getCustomFieldReturn.value.content == 'Test Solution'
