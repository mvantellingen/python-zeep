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
        obj = custom_type(_any_1=some_type)
