from lxml import etree

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
    obj = custom_type.parse(expected)
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
    obj = custom_element.parse(expected)
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
    obj = custom_type.parse(expected)
    assert obj.item_1 == '1'
    assert obj.item_2 is None
    assert obj.item_3 == ['3']
    assert obj.item_4 is None
