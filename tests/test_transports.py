import pytest
import requests_mock
from pretend import stub
from requests_mock import NoMockAddress

from zeep import cache, transports
from zeep.transports import AbstractTransport


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
        m.get("http://tests.python-zeep.org/test.xml", text="x")
        result = transport.load("http://tests.python-zeep.org/test.xml")

        assert result == b"x"


@pytest.mark.skip(reason="It isn't the best test")
@pytest.mark.requests
def test_modify_log_request():

    class MyCustomTransport(AbstractTransport):

        def replace_custom_elements_in_log_request_message(self, log_message):
            new_log_message = log_message.replace('x', 'y')
            return new_log_message

        def replace_custom_elements_in_log_response_message(self, log_message):
            import re
            new_log_message = re.sub(
                r'<title.*title>',
                '<title>I change the title</title>',
                log_message
            )
            new_log_message = re.sub(
                r'<h1.*h1>',
                '<h1>I change the h1</h1>',
                new_log_message
            )
            return new_log_message

    import logging.config
    logging.basicConfig(level=logging.DEBUG)

    try:
        transport = MyCustomTransport()
        # we send 'x' in request, and in log, we show 'y'
        transport.post(address="http://tests.python-zeep.org/test.xml", message="x", headers=None)
        # in response log, we change <title> and <h1>
        # show in console
    except NoMockAddress:
        assert True


def test_settings_set_context_timeout():
    transport = transports.Transport(cache=cache)

    assert transport.operation_timeout is None
    with transport.settings(timeout=120):
        assert transport.operation_timeout == 120

        with transport.settings(timeout=90):
            assert transport.operation_timeout == 90
        assert transport.operation_timeout == 120
    assert transport.operation_timeout is None
