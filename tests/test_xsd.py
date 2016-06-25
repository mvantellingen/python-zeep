import pytest
from lxml import etree

from tests.utils import assert_nodes_equal, render_node
from zeep import xsd


def test_container_elements():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'username'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'password'),
                    xsd.String()),
                xsd.Any(),
            ])
        ))

    # sequences
    custom_type(username='foo', password='bar')


def test_create_node():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'username'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'password'),
                    xsd.String()),
            ])
        ))

    # sequences
    obj = custom_type(username='foo', password='bar')

    expected = """
      <document>
        <ns0:authentication xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:username>foo</ns0:username>
          <ns0:password>bar</ns0:password>
        </ns0:authentication>
      </document>
    """
    node = etree.Element('document')
    custom_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_element_simple_type():
    elm = xsd.Element(
        '{http://tests.python-zeep.org/}item', xsd.String())
    obj = elm('foo')

    expected = """
      <document>
        <ns0:item xmlns:ns0="http://tests.python-zeep.org/">foo</ns0:item>
      </document>
    """
    node = etree.Element('document')
    elm.render(node, obj)
    assert_nodes_equal(expected, node)


def test_nil_elements():
    custom_type = xsd.Element(
        '{http://tests.python-zeep.org/}container',
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    '{http://tests.python-zeep.org/}item_1',
                    xsd.ComplexType(
                        xsd.Sequence([
                            xsd.Element(
                                '{http://tests.python-zeep.org/}item_1_1',
                                xsd.String())
                        ]),
                    ),
                    nillable=True),
                xsd.Element(
                    '{http://tests.python-zeep.org/}item_2',
                    xsd.DateTime(), nillable=True),
                xsd.Element(
                    '{http://tests.python-zeep.org/}item_3',
                    xsd.String(), min_occurs=0, nillable=False),
                xsd.Element(
                    '{http://tests.python-zeep.org/}item_4',
                    xsd.ComplexType(
                        xsd.Sequence([
                            xsd.Element(
                                '{http://tests.python-zeep.org/}item_4_1',
                                xsd.String(), nillable=True)
                        ])
                    )
                ),
            ])
        ))
    obj = custom_type(item_1=None, item_2=None, item_3=None, item_4={})

    expected = """
      <document>
        <ns0:container xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:item_1/>
          <ns0:item_2/>
          <ns0:item_4>
            <ns0:item_4_1/>
          </ns0:item_4>
        </ns0:container>
      </document>
    """
    node = render_node(custom_type, obj)
    assert_nodes_equal(expected, node)


def test_invalid_kwarg():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'username'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'password'),
                    xsd.String()),
            ])
        ))

    with pytest.raises(TypeError):
        custom_type(something='is-wrong')


def test_invalid_kwarg_simple_type():
    elm = xsd.Element(
        '{http://tests.python-zeep.org/}item', xsd.String())

    with pytest.raises(TypeError):
        elm(something='is-wrong')


def test_any():
    some_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'doei'),
        xsd.String())

    complex_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'complex'),
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

    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'hoi'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Any(),
                xsd.Any(),
                xsd.Any(),
            ])
        ))

    any_1 = xsd.AnyObject(some_type, "DOEI!")
    any_2 = xsd.AnyObject(
        complex_type, complex_type(item_1='val_1', item_2='val_2'))
    any_3 = xsd.AnyObject(
        complex_type, [
            complex_type(item_1='val_1_1', item_2='val_1_2'),
            complex_type(item_1='val_2_1', item_2='val_2_2'),
        ])

    obj = custom_type(_value_1=any_1, _value_2=any_2, _value_3=any_3)

    expected = """
      <document>
        <ns0:hoi xmlns:ns0="http://tests.python-zeep.org/">
          <ns0:doei>DOEI!</ns0:doei>
          <ns0:complex>
            <ns0:item_1>val_1</ns0:item_1>
            <ns0:item_2>val_2</ns0:item_2>
          </ns0:complex>
          <ns0:complex>
            <ns0:item_1>val_1_1</ns0:item_1>
            <ns0:item_2>val_1_2</ns0:item_2>
          </ns0:complex>
          <ns0:complex>
            <ns0:item_1>val_2_1</ns0:item_1>
            <ns0:item_2>val_2_2</ns0:item_2>
          </ns0:complex>
        </ns0:hoi>
      </document>
    """
    node = etree.Element('document')
    custom_type.render(node, obj)
    assert_nodes_equal(expected, node)


def test_any_type_check():
    some_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'doei'),
        xsd.String())

    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'complex'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Any(),
            ])
        ))
    with pytest.raises(TypeError):
        custom_type(_any_1=some_type)


def test_choice():
    root = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'kies'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'pre'),
                    xsd.String()),
                xsd.Choice([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_1'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_2'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_3'),
                        xsd.String()),
                ], max_occurs=3),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'post'),
                    xsd.String()),
            ])
        )
    )

    obj = root('foo', _value_1=[{'item_1': [20, 30]}, {'item_2': 'nyet'}])
    node = etree.Element('document')
    root.render(node, obj)
    assert etree.tostring(node)

    expected = """
    <document>
      <ns0:kies xmlns:ns0="http://tests.python-zeep.org/">
        <ns0:pre>foo</ns0:pre>
        <ns0:item_1>20</ns0:item_1>
        <ns0:item_1>30</ns0:item_1>
        <ns0:item_2>nyet</ns0:item_2>
        <ns0:post/>
      </ns0:kies>
    </document>
    """.strip()
    assert_nodes_equal(expected, node)


def test_choice_determinst():
    root = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'kies'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Choice([
                    xsd.Sequence([
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_1'),
                            xsd.String()),
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_2'),
                            xsd.String()),
                    ]),
                    xsd.Sequence([
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_2'),
                            xsd.String()),
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_1'),
                            xsd.String()),
                    ]),
                ])
            ])
        )
    )

    obj = root(_value_1={'item_1': 'item-1', 'item_2': 'item-2'})
    node = etree.Element('document')
    root.render(node, obj)
    assert etree.tostring(node)

    expected = """
    <document>
      <ns0:kies xmlns:ns0="http://tests.python-zeep.org/">
        <ns0:item_1>item-1</ns0:item_1>
        <ns0:item_2>item-2</ns0:item_2>
      </ns0:kies>
    </document>
    """.strip()
    assert_nodes_equal(expected, node)


@pytest.mark.xfail
def test_sequence():
    root = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'container'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Sequence([
                    xsd.Sequence([
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_1'),
                            xsd.String()),
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_2'),
                            xsd.String()),
                    ], min_occurs=2, max_occurs=2),
                    xsd.Sequence([
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_3'),
                            xsd.String()),
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_4'),
                            xsd.String()),
                    ]),
                ])
            ])
        )
    )
    root(
        _sequence_1=[
            {
                'item_1': 'foo',
                'item_2': 'bar',
            },
            {
                'item_1': 'foo',
                'item_2': 'bar',
            },
        ],
        item_3='foo',
        item_4='bar',
    )
