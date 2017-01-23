import datetime
from collections import OrderedDict

from lxml import etree

from zeep import xsd
from zeep.xsd.valueobjects import CompoundValue


def serialize_object(obj):
    """Serialize zeep objects to native python data structures"""
    if obj is None:
        return obj

    if isinstance(obj, etree._Element):
        return obj

    if isinstance(obj, list):
        return [serialize_object(sub) for sub in obj]

    result = OrderedDict()
    for key in obj:
        value = obj[key]
        if isinstance(value, (list, CompoundValue)):
            value = serialize_object(value)
        result[key] = value
    return result


def create_xml_soap_map(values):
    """Create an http://xml.apache.org/xml-soap#Map value."""
    Map = xsd.ComplexType(
        xsd.Sequence([
            xsd.Element(
                'item',
                xsd.AnyType(),
                min_occurs=1,
                max_occurs="unbounded"),
            ]),
        qname=etree.QName('{http://xml.apache.org/xml-soap}Map'))

    KeyValueData = xsd.Element(
        '{http://xml.apache.org/xml-soap}KeyValueData',
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    'key',
                    xsd.AnyType(),
                ),
                xsd.Element(
                    'value',
                    xsd.AnyType(),
                ),
            ]),
        ),
    )

    return Map(item=[
        KeyValueData(
            xsd.AnyObject(xsd.String(), key),
            xsd.AnyObject(guess_xsd_type(value), value)
        ) for key, value in values.items()
    ])


def guess_xsd_type(obj):
    """Return the XSD Type for the given object"""
    if isinstance(obj, bool):
        return xsd.Boolean()
    if isinstance(obj, int):
        return xsd.Integer()
    if isinstance(obj, float):
        return xsd.Float()
    if isinstance(obj, datetime.datetime):
        return xsd.DateTime()
    if isinstance(obj, datetime.date):
        return xsd.Date()
    return xsd.String()


def Nil():
    """Return an xsi:nil element"""
    return xsd.AnyObject(None, None)
