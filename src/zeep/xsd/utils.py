from defusedxml.lxml import fromstring
from lxml import etree

from six.moves import range
from six.moves.urllib.parse import urlparse
from zeep.exceptions import XMLSyntaxError
from zeep.parser import absolute_location


class NamePrefixGenerator(object):
    def __init__(self, prefix='_value_'):
        self._num = 1
        self._prefix = prefix

    def get_name(self):
        retval = '%s%d' % (self._prefix, self._num)
        self._num += 1
        return retval


class UniqueNameGenerator(object):
    def __init__(self):
        self._unique_count = {}

    def create_name(self, name):
        if name in self._unique_count:
            self._unique_count[name] += 1
            return '%s__%d' % (name, self._unique_count[name])
        else:
            self._unique_count[name] = 0
            return name


class ImportResolver(etree.Resolver):
    """Custom lxml resolve to use the transport object"""
    def __init__(self, transport):
        self.transport = transport

    def resolve(self, url, pubid, context):
        if urlparse(url).scheme in ('http', 'https'):
            content = self.transport.load(url)
            return self.resolve_string(content, context)


def parse_xml(content, transport, base_url=None):
    parser = etree.XMLParser(remove_comments=True, resolve_entities=False)
    parser.resolvers.add(ImportResolver(transport))
    try:
        return fromstring(content, parser=parser, base_url=base_url)
    except etree.XMLSyntaxError as exc:
        raise XMLSyntaxError("Invalid XML content received (%s)" % exc.message)


def load_external(url, transport, base_url=None):
    if base_url:
        url = absolute_location(url, base_url)

    response = transport.load(url)
    return parse_xml(response, transport, base_url)


def max_occurs_iter(max_occurs, items=None):
    assert max_occurs is not None
    generator = range(0, max_occurs if max_occurs != 'unbounded' else 2**31-1)

    if items is not None:
        for i, sub_kwargs in zip(generator, items):
            yield sub_kwargs
    else:
        for i in generator:
            yield i
