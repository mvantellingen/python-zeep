import logging

from zeep.utils import qname_attr
from zeep.xsd.const import xsd_ns, xsi_ns
from zeep.xsd.types.base import Type
from zeep.xsd.valueobjects import AnyObject

logger = logging.getLogger(__name__)

__all__ = ['AnyType']


class AnyType(Type):
    _default_qname = xsd_ns('anyType')
    _attributes_unwrapped = []
    _element = None

    def render(self, parent, value, xsd_type=None, render_path=None):
        if isinstance(value, AnyObject):
            if value.xsd_type is None:
                parent.set(xsi_ns('nil'), 'true')
            else:
                value.xsd_type.render(parent, value.value, None, render_path)
                parent.set(xsi_ns('type'), value.xsd_type.qname)
        elif hasattr(value, '_xsd_elm'):
            value._xsd_elm.render(parent, value, render_path)
            parent.set(xsi_ns('type'), value._xsd_elm.qname)
        else:
            parent.text = self.xmlvalue(value)

    def parse_xmlelement(self, xmlelement, schema=None, allow_none=True,
                         context=None):
        xsi_type = qname_attr(xmlelement, xsi_ns('type'))
        xsi_nil = xmlelement.get(xsi_ns('nil'))
        children = list(xmlelement.getchildren())

        # Handle xsi:nil attribute
        if xsi_nil == 'true':
            return None

        # Check if a xsi:type is defined and try to parse the xml according
        # to that type.
        if xsi_type and schema:
            xsd_type = schema.get_type(xsi_type, fail_silently=True)

            # If we were unable to resolve a type for the xsi:type (due to
            # buggy soap servers) then we just return the lxml element.
            if not xsd_type:
                return children

            # If the xsd_type is xsd:anyType then we will recurs so ignore
            # that.
            if isinstance(xsd_type, self.__class__):
                return xmlelement.text or None

            return xsd_type.parse_xmlelement(
                xmlelement, schema, context=context)

        # If no xsi:type is set and the element has children then there is
        # not much we can do. Just return the children
        elif children:
            return children

        elif xmlelement.text is not None:
            return self.pythonvalue(xmlelement.text)

        return None

    def resolve(self):
        return self

    def xmlvalue(self, value):
        return value

    def pythonvalue(self, value, schema=None):
        return value
