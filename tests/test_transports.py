import pytest
import requests_mock
from pretend import stub

from zeep import cache, transports



@pytest.mark.requests
def test_no_cache():
    transport = transports.Transport(cache=None)
    assert transport.cache is None


@pytest.mark.requests
def test_custom_cache():
    transport = transports.Transport(cache=cache.SqliteCache())
    assert isinstance(transport.cache, cache.SqliteCache)


@pytest.mark.requests
def test_load():
    cache = stub(get=lambda url: None, add=lambda url, content: None)
    transport = transports.Transport(cache=cache)

    with requests_mock.mock() as m:
        m.get('http://tests.python-zeep.org/test.xml', text='x')
        result = transport.load('http://tests.python-zeep.org/test.xml')

        assert result == b'x'
