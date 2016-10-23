from lxml import etree

from tests.utils import load_xml
from zeep import xsd
from zeep.xsd.schema import Schema


def test_sequence_parse_basic():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.String()),
            ])
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


def test_sequence_parse_basic_with_attrs():
    custom_element = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.String()),
            ]),
            [
                xsd.Attribute(
                    etree.QName('http://tests.python-zeep.org/', 'attr_1'),
                    xsd.String()),
                xsd.Attribute('attr_2', xsd.String()),
            ]
        ))
    expected = etree.fromstring("""
        <ns0:authentication xmlns:ns0="http://tests.python-zeep.org/" ns0:attr_1="x" attr_2="y">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:authentication>
    """)
    obj = custom_element.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2 == 'bar'
    assert obj.attr_1 == 'x'
    assert obj.attr_2 == 'y'


def test_sequence_parse_with_optional():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'container'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.ComplexType(
                        xsd.Sequence([
                            xsd.Element(
                                etree.QName('http://tests.python-zeep.org/', 'item_2_1'),
                                xsd.String(),
                                nillable=True)
                        ])
                    )
                ),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_3'),
                    xsd.String(),
                    max_occurs=2),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_4'),
                    xsd.String(),
                    min_occurs=0),
            ])
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


def test_sequence_parse_regression():
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


def test_sequence_parse_anytype():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'container'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.AnyType()),
            ])
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'


def test_sequence_parse_anytype_nil():
    schema = xsd.Schema(load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <xsd:schema xmlns:tns="http://tests.python-zeep.org/"
          xmlns:xsd="http://www.w3.org/2001/XMLSchema"
          elementFormDefault="qualified"
          targetNamespace="http://tests.python-zeep.org/">
          <xsd:element name="container">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element minOccurs="0" maxOccurs="1" name="item_1" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """))

    container = schema.get_element('{http://tests.python-zeep.org/}container')

    expected = etree.fromstring("""
        <ns0:container
            xmlns:ns0="http://tests.python-zeep.org/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <ns0:item_1 xsi:type="xsd:anyType"/>
        </ns0:container>
    """)
    obj = container.parse(expected, schema)
    assert obj.item_1 is None


def test_sequence_parse_anytype_obj():
    value_type = xsd.ComplexType(
        xsd.Sequence([
            xsd.Element(
                '{http://tests.python-zeep.org/}value',
                xsd.Integer()),
        ])
    )

    schema = Schema(
        etree.Element(
            '{http://www.w3.org/2001/XMLSchema}Schema',
            targetNamespace='http://tests.python-zeep.org/'))

    root = list(schema._schemas.values())[0]
    root.register_type('{http://tests.python-zeep.org/}something', value_type)

    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'container'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.AnyType()),
            ])
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


def test_sequence_parse_choice():
    schema_doc = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <schema
            xmlns="http://www.w3.org/2001/XMLSchema"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/tst"
            elementFormDefault="qualified"
            targetNamespace="http://tests.python-zeep.org/tst">
          <element name="container">
            <complexType>
              <sequence>
                <choice>
                  <element name="item_1" type="xsd:string" />
                  <element name="item_2" type="xsd:string" />
                </choice>
                <element name="item_3" type="xsd:string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """)

    xml = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <tst:container
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:tst="http://tests.python-zeep.org/tst">
          <tst:item_1>blabla</tst:item_1>
          <tst:item_3>haha</tst:item_3>
        </tst:container>
    """)

    schema = xsd.Schema(schema_doc)
    elm = schema.get_element('{http://tests.python-zeep.org/tst}container')
    result = elm.parse(xml, schema)
    assert result.item_1 == 'blabla'
    assert result.item_3 == 'haha'


def test_sequence_parse_choice_max_occurs():
    schema_doc = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <schema
            xmlns="http://www.w3.org/2001/XMLSchema"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/tst"
            elementFormDefault="qualified"
            targetNamespace="http://tests.python-zeep.org/tst">
          <element name="container">
            <complexType>
              <sequence>
                <choice maxOccurs="2">
                  <element name="item_1" type="xsd:string" />
                  <element name="item_2" type="xsd:string" />
                </choice>
                <element name="item_3" type="xsd:string" />
              </sequence>
              <attribute name="item_1" type="xsd:string" use="optional" />
              <attribute name="item_2" type="xsd:string" use="optional" />
            </complexType>
          </element>
        </schema>
    """)

    xml = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <tst:container
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:tst="http://tests.python-zeep.org/tst">
          <tst:item_1>item-1-1</tst:item_1>
          <tst:item_1>item-1-2</tst:item_1>
          <tst:item_3>item-3</tst:item_3>
        </tst:container>
    """)

    schema = xsd.Schema(schema_doc)
    elm = schema.get_element('{http://tests.python-zeep.org/tst}container')
    result = elm.parse(xml, schema)
    assert result._value_1 == [
        {'item_1': 'item-1-1'},
        {'item_1': 'item-1-2'},
    ]

    assert result.item_3 == 'item-3'


def test_sequence_parse_choice_sequence_max_occurs():
    schema_doc = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <schema
            xmlns="http://www.w3.org/2001/XMLSchema"
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/tst"
            elementFormDefault="qualified"
            targetNamespace="http://tests.python-zeep.org/tst">
          <element name="container">
            <complexType>
              <sequence>
                <choice maxOccurs="3">
                  <sequence>
                    <element name="item_1" type="xsd:string" />
                    <element name="item_2" type="xsd:string" />
                  </sequence>
                  <element name="item_3" type="xsd:string" />
                </choice>
                <element name="item_4" type="xsd:string" />
              </sequence>
            </complexType>
          </element>
        </schema>
    """)

    xml = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <tst:container
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:tst="http://tests.python-zeep.org/tst">
          <tst:item_1>text-1</tst:item_1>
          <tst:item_2>text-2</tst:item_2>
          <tst:item_1>text-1</tst:item_1>
          <tst:item_2>text-2</tst:item_2>
          <tst:item_3>text-3</tst:item_3>
          <tst:item_4>text-4</tst:item_4>
        </tst:container>
    """)

    schema = xsd.Schema(schema_doc)
    elm = schema.get_element('{http://tests.python-zeep.org/tst}container')
    result = elm.parse(xml, schema)
    assert result._value_1 == [
        {'item_1': 'text-1', 'item_2': 'text-2'},
        {'item_1': 'text-1', 'item_2': 'text-2'},
        {'item_3': 'text-3'},
    ]
    assert result.item_4 == 'text-4'


def test_sequence_parse_anytype_regression_17():
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


def test_sequence_min_occurs_2():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.String()),
            ], min_occurs=2, max_occurs=2)
        ))

    # INIT
    elm = custom_type(_value_1=[
        {'item_1': 'foo-1', 'item_2': 'bar-1'},
        {'item_1': 'foo-2', 'item_2': 'bar-2'},
    ])

    assert elm._value_1 == [
        {'item_1': 'foo-1', 'item_2': 'bar-1'},
        {'item_1': 'foo-2', 'item_2': 'bar-2'},
    ]

    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj._value_1 == [
        {
            'item_1': 'foo',
            'item_2': 'bar',
        },
        {
            'item_1': 'foo',
            'item_2': 'bar',
        },
    ]


def test_all_basic():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.All([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.String()),
            ])
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2 == 'bar'


def test_group_optional():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Group(
                etree.QName('http://tests.python-zeep.org/', 'foobar'),
                xsd.Sequence([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_1'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_2'),
                        xsd.String()),
                ]),
                min_occurs=1)
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
    assert not hasattr(obj, 'foobar')


def test_group_min_occurs_2():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Group(
                etree.QName('http://tests.python-zeep.org/', 'foobar'),
                xsd.Sequence([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_1'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_2'),
                        xsd.String()),
                ]),
                min_occurs=2, max_occurs=2)
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj._value_1 == [
        {'item_1': 'foo', 'item_2': 'bar'},
        {'item_1': 'foo', 'item_2': 'bar'},
    ]
    assert not hasattr(obj, 'foobar')


def test_group_min_occurs_2_sequence_min_occurs_2():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Group(
                etree.QName('http://tests.python-zeep.org/', 'foobar'),
                xsd.Sequence([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_1'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_2'),
                        xsd.String()),
                ], min_occurs=2, max_occurs=2),
                min_occurs=2, max_occurs=2)
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>bar</ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj._value_1 == [
        {'_value_1': [
            {'item_1': 'foo', 'item_2': 'bar'},
            {'item_1': 'foo', 'item_2': 'bar'},
        ]},
        {'_value_1': [
            {'item_1': 'foo', 'item_2': 'bar'},
            {'item_1': 'foo', 'item_2': 'bar'},
        ]},
    ]
    assert not hasattr(obj, 'foobar')


def test_nested_complex_type():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.ComplexType(
                        xsd.Sequence([
                            xsd.Element(
                                '{http://tests.python-zeep.org/}item_2a',
                                xsd.String()),
                            xsd.Element(
                                '{http://tests.python-zeep.org/}item_2b',
                                xsd.String()),
                        ])
                    )
                )
            ])
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>
            <ns0:item_2a>2a</ns0:item_2a>
            <ns0:item_2b>2b</ns0:item_2b>
          </ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2.item_2a == '2a'
    assert obj.item_2.item_2b == '2b'


def test_nested_complex_type_optional():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.ComplexType(
                        xsd.Sequence([
                            xsd.Choice([
                                xsd.Element(
                                    '{http://tests.python-zeep.org/}item_2a1',
                                    xsd.String()),
                                xsd.Element(
                                    '{http://tests.python-zeep.org/}item_2a2',
                                    xsd.String()),
                            ]),
                            xsd.Element(
                                '{http://tests.python-zeep.org/}item_2b',
                                xsd.String()),
                        ])
                    ),
                    min_occurs=0, max_occurs='unbounded'
                )
            ])
        ))
    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2 == []

    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2/>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2 == []

    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>
            <ns0:item_2a1>x</ns0:item_2a1>
          </ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2[0].item_2a1 == 'x'
    assert obj.item_2[0].item_2b is None

    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
          <ns0:item_2>
            <ns0:item_2a1>x</ns0:item_2a1>
            <ns0:item_2b/>
          </ns0:item_2>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2[0].item_2a1 == 'x'
    assert obj.item_2[0].item_2b is None


def test_nested_choice_optional():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Choice([
                        xsd.Element(
                            '{http://tests.python-zeep.org/}item_2',
                            xsd.String()),
                        xsd.Element(
                            '{http://tests.python-zeep.org/}item_3',
                            xsd.String()),
                    ],
                    min_occurs=0, max_occurs=1
                ),
            ])
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

    expected = etree.fromstring("""
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1>foo</ns0:item_1>
        </ns0:container>
    """)
    obj = custom_type.parse(expected, None)
    assert obj.item_1 == 'foo'
    assert obj.item_2 is None
    assert obj.item_3 is None


def test_union():
    schema_doc = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/tst"
            elementFormDefault="qualified"
            targetNamespace="http://tests.python-zeep.org/tst">

          <xsd:element name="State" type="tns:StateType"/>

          <xsd:complexType name="StateType">
            <xsd:simpleContent>
                <xsd:extension base="tns:StateBaseType">
                  <xsd:anyAttribute namespace="##other" processContents="lax"/>
                </xsd:extension>
            </xsd:simpleContent>
          </xsd:complexType>
          <xsd:simpleType name="tns:StateBaseType">
            <xsd:union memberTypes="tns:Type1 tns:Type2"/>
          </xsd:simpleType>

          <xsd:simpleType name="Type1">
            <xsd:restriction base="xsd:NMTOKEN">
              <xsd:maxLength value="255"/>
              <xsd:enumeration value="Idle"/>
              <xsd:enumeration value="Processing"/>
              <xsd:enumeration value="Stopped"/>
            </xsd:restriction>
          </xsd:simpleType>

          <xsd:simpleType name="Type2">
            <xsd:restriction base="xsd:NMTOKEN">
              <xsd:maxLength value="255"/>
              <xsd:enumeration value="Paused"/>
            </xsd:restriction>
          </xsd:simpleType>
        </xsd:schema>
    """)

    xml = load_xml(b"""
        <?xml version="1.0" encoding="utf-8"?>
        <tst:State xmlns:tst="http://tests.python-zeep.org/tst">Idle</tst:State>
    """)

    schema = xsd.Schema(schema_doc)
    elm = schema.get_element('{http://tests.python-zeep.org/tst}State')
    result = elm.parse(xml, schema)
    assert result._value_1 == 'Idle'
