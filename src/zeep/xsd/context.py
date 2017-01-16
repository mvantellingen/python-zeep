class ParserContext(object):
    """Parser context when parsing wsdl/xsd files"""
    def __init__(self):
        # Mapping between internal nodes and original location
        self.schema_locations = {}


class XmlParserContext(object):
    """Parser context when parsing XML elements"""

    def __init__(self):
        self.schemas = []
