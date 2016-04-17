import pytest
from lxml import etree

from tests.utils import assert_nodes_equal
from zeep import xsd


def test_create_node():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            children=[
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'username'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'password'),
                    xsd.String()),
            ]
        ))
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


def test_any():
    some_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'doei'),
        xsd.String())

    complex_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'complex'),
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

    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'hoi'),
        xsd.ComplexType(
            children=[
                xsd.Any(),
                xsd.Any(),
                xsd.Any(),
            ]
        ))

    any_1 = xsd.AnyObject(some_type, "DOEI!")
    any_2 = xsd.AnyObject(
        complex_type, complex_type(item_1='val_1', item_2='val_2'))
    any_3 = xsd.AnyObject(
        complex_type, [
            complex_type(item_1='val_1_1', item_2='val_1_2'),
            complex_type(item_1='val_2_1', item_2='val_2_2'),
        ])

    obj = custom_type(_any_1=any_1, _any_2=any_2, _any_3=any_3)

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
            children=[
                xsd.Any(),
            ]
        ))
    with pytest.raises(TypeError):
        custom_type(_any_1=some_type)


def test_choice():
    root = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'kies'),
        xsd.ComplexType(
            children=[
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
            ]
        )
    )

    obj = root('foo', item_1=[20, 30], item_2='nyet')
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
