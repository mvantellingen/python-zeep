import pytest
import requests_mock
from pretend import stub

from zeep import transports


@pytest.mark.requests
def test_load():
    cache = stub(get=lambda url: None, add=lambda url, content: None)
    transport = transports.Transport(cache=cache)

    with requests_mock.mock() as m:
        m.get('http://tests.python-zeep.org/test.xml', text='x')
        result = transport.load('http://tests.python-zeep.org/test.xml')

        assert result == b'x'
