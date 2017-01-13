from collections import OrderedDict

from lxml import etree

from zeep.xsd.valueobjects import CompoundValue


def serialize_object(obj, dict_type=OrderedDict):
    """Serialize zeep objects to native python data structures"""
    if obj is None:
        return obj

    if isinstance(obj, etree._Element):
        return obj

    if isinstance(obj, list):
        return [serialize_object(sub, dict_type=dict_type) for sub in obj]

    if isinstance(obj, (dict, CompoundValue)):
        result = dict_type()
        for key in obj:
            value = obj[key]
            result[key] = serialize_object(value, dict_type=dict_type)
        return result

    return obj
