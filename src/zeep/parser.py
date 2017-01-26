import os

from defusedxml.lxml import fromstring
from lxml import etree

from six.moves.urllib.parse import urljoin, urlparse
from zeep.exceptions import XMLSyntaxError


def parse_xml(content, base_url=None, recover=False):
    parser = etree.XMLParser(
        remove_comments=True, recover=recover, resolve_entities=False)
    try:
        return fromstring(content, parser=parser, base_url=base_url)
    except etree.XMLSyntaxError as exc:
        raise XMLSyntaxError("Invalid XML content received (%s)" % exc)


def load_external(url, transport, base_url=None):
    if base_url:
        url = absolute_location(url, base_url)

    response = transport.load(url)
    return parse_xml(response, base_url)


def absolute_location(location, base):
    if location == base:
        return location

    if urlparse(location).scheme in ('http', 'https'):
        return location

    if base and urlparse(base).scheme in ('http', 'https'):
        return urljoin(base, location)
    else:
        if os.path.isabs(location):
            return location
        if base:
            return os.path.realpath(
                os.path.join(os.path.dirname(base), location))
    return location


def is_relative_path(value):
    """Check if the given value is a relative path"""
    if urlparse(value).scheme in ('http', 'https', 'file'):
        return False
    return not os.path.isabs(value)
