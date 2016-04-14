from lxml import etree

from zeep import xsd
from zeep.helpers import serialize_object


def test_serialize():
    custom_type = xsd.Element(
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
                    max_occurs=2
                )

            ]
        ))

    obj = custom_type(
        name='foo', attr='x',
        items=[
            {'x': 'bla', 'y': {'x': 'deep'}},
            {'x': 'foo', 'y': {'x': 'deeper'}},
        ])

    result = serialize_object(obj)
    assert result == {
        'name': 'foo',
        'attr': 'x',
        'items': [
            {'x': 'bla', 'y': {'x': 'deep'}},
            {'x': 'foo', 'y': {'x': 'deeper'}},
        ]
    }
