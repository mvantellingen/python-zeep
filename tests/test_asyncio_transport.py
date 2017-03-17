from asyncio import coroutine
import pytest
from pretend import stub
import requests_mock
from lxml import etree
from aioresponses import aioresponses

from zeep import cache, asyncio


@pytest.mark.requests
def test_no_cache(event_loop):
    transport = asyncio.AsyncTransport(loop=event_loop)
    assert transport.cache is None


@pytest.mark.requests
def test_load(event_loop):
    cache = stub(get=lambda url: None, add=lambda url, content: None)
    transport = asyncio.AsyncTransport(loop=event_loop, cache=cache)

    with aioresponses() as m:
        m.get('http://tests.python-zeep.org/test.xml', body='x')
        result = transport.load('http://tests.python-zeep.org/test.xml')
        assert result == b'x'


@pytest.mark.requests
@pytest.mark.asyncio
def test_load_sync(event_loop):
    cache = stub(get=lambda url: None, add=lambda url, content: None)
    transport = asyncio.AsyncTransport(loop=event_loop, cache=cache)

    @coroutine
    def async_getter():
        return transport.load('http://tests.python-zeep.org/test.xml')

    with requests_mock.mock() as m:
        m.get('http://tests.python-zeep.org/test.xml', text='x')
        result = yield from async_getter()

        assert result == b'x'


@pytest.mark.requests
@pytest.mark.asyncio
async def test_post(event_loop):
    cache = stub(get=lambda url: None, add=lambda url, content: None)
    transport = asyncio.AsyncTransport(loop=event_loop, cache=cache)

    envelope = etree.Element('Envelope')

    with aioresponses() as m:
        m.post('http://tests.python-zeep.org/test.xml', body='x')
        result = await transport.post_xml(
            'http://tests.python-zeep.org/test.xml',
            envelope=envelope,
            headers={})

        assert result.content == b'x'
