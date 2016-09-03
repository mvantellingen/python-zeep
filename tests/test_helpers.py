from lxml import etree
from collections import OrderedDict

from tests.utils import load_xml
from zeep import xsd
from zeep.helpers import serialize_object


def test_serialize_simple():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'name'),
                    xsd.String()),
                xsd.Attribute(
                    etree.QName('http://tests.python-zeep.org/', 'attr'),
                    xsd.String()),
            ])
        ))

    obj = custom_type(name='foo', attr='x')
    assert obj.name == 'foo'
    assert obj.attr == 'x'

    result = serialize_object(obj)

    assert result == {
        'name': 'foo',
        'attr': 'x',
    }


def test_serialize_nested_complex_type():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'items'),
                    xsd.ComplexType(
                        xsd.Sequence([
                            xsd.Element(
                                etree.QName('http://tests.python-zeep.org/', 'x'),
                                xsd.String()),
                            xsd.Element(
                                etree.QName('http://tests.python-zeep.org/', 'y'),
                                xsd.ComplexType(
                                    xsd.Sequence([
                                        xsd.Element(
                                            etree.QName('http://tests.python-zeep.org/', 'x'),
                                            xsd.String()),
                                    ])
                                )
                            )
                        ])
                    ),
                    max_occurs=2
                )
            ])
        ))

    obj = custom_type(
        items=[
            {'x': 'bla', 'y': {'x': 'deep'}},
            {'x': 'foo', 'y': {'x': 'deeper'}},
        ])

    assert len(obj.items) == 2
    obj.items[0].x == 'bla'
    obj.items[0].y.x == 'deep'
    obj.items[1].x == 'foo'
    obj.items[1].y.x == 'deeper'

    result = serialize_object(obj)

    assert result == {
        'items': [
            {'x': 'bla', 'y': {'x': 'deep'}},
            {'x': 'foo', 'y': {'x': 'deeper'}},
        ]
    }


def test_nested_complex_types():
    schema = xsd.Schema(load_xml("""
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:tns="http://tests.python-zeep.org/"
                targetNamespace="http://tests.python-zeep.org/"
                elementFormDefault="qualified">
          <xsd:element name="container">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="item" type="tns:item"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>
          <xsd:complexType name="item">
            <xsd:sequence>
              <xsd:element name="item_1" type="xsd:string"/>
            </xsd:sequence>
          </xsd:complexType>
        </xsd:schema>
    """))

    container_elm = schema.get_element('{http://tests.python-zeep.org/}container')
    item_type = schema.get_type('{http://tests.python-zeep.org/}item')

    instance = container_elm(item=item_type(item_1='foo'))
    result = serialize_object(instance)
    assert isinstance(result, dict), type(result)
    assert isinstance(result['item'], dict), type(result['item'])
    assert result['item']['item_1'] == 'foo'
