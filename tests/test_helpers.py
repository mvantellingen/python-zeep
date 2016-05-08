from lxml import etree

from zeep import xsd
from zeep.helpers import serialize_object


def test_serialize():
    custom_element = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            children=[
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'name'),
                    xsd.String()),
                xsd.Attribute(
                    etree.QName('http://tests.python-zeep.org/', 'attr'),
                    xsd.String()),
                xsd.ListElement(
                    etree.QName('http://tests.python-zeep.org/', 'items'),
                    xsd.ComplexType(
                        children=[
                            xsd.Element(
                                etree.QName('http://tests.python-zeep.org/', 'x'),
                                xsd.String()),
                            xsd.Element(
                                etree.QName('http://tests.python-zeep.org/', 'y'),
                                xsd.ComplexType(
                                    children=[
                                        xsd.Element(
                                            etree.QName('http://tests.python-zeep.org/', 'x'),
                                            xsd.String()),
                                    ]
                                )
                            )
                        ]
                    ),
                    max_occurs=3
                )

            ]
        ))

    obj = custom_element(
        name='foo', attr='x',
        items=[
            {'x': 'bla', 'y': {'x': 'deep'}},
            {'x': 'foo', 'y': {'x': 'deeper'}},
            {'x': 'nil', 'y': None},
        ])

    result = serialize_object(obj)
    assert result == {
        'name': 'foo',
        'attr': 'x',
        'items': [
            {'x': 'bla', 'y': {'x': 'deep'}},
            {'x': 'foo', 'y': {'x': 'deeper'}},
            {'x': 'nil', 'y': None}
        ]
    }


def test_serialize_list():
    custom_element = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            children=[
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'name'),
                    xsd.String()),
            ]
        ))

    objs = [
        custom_element(name='foo'),
        custom_element(name='bla')
    ]
    result = serialize_object(objs)
    assert result == [
        {'name': 'foo'},
        {'name': 'bla'},
    ]


def test_serialize_none():
    assert serialize_object(None) is None
