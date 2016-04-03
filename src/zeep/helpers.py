def serialize_object(obj):
    """Serialize zeep objects to native python data structures"""
    if obj is None:
        return obj

    if isinstance(obj, list):
        return [sub._xsd_type.serialize(sub) for sub in obj]
    return obj._xsd_type.serialize(obj)
