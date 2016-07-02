from collections import OrderedDict


def serialize_object(obj):
    """Serialize zeep objects to native python data structures"""
    if obj is None:
        return obj

    if isinstance(obj, list):
        return [serialize_object(sub) for sub in obj]

    result = OrderedDict()
    for key in obj:
        if key == '_xsd_elm':
            continue

        result[key] = getattr(obj, key)
    return result
