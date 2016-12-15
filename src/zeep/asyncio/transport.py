"""
Adds asyncio support to Zeep. Contains Python 3.5+ only syntax!

"""
import asyncio

import aiohttp

from zeep.transports import Transport
from zeep.wsdl.utils import etree_to_string

__all__ = ['AsyncTransport']


class AsyncTransport(Transport):
    """Asynchronous Transport class using aiohttp."""
    supports_async = True

    def __init__(self, loop, *args, **kwargs):
        self.loop = loop if loop else asyncio.get_event_loop()
        super().__init__(*args, **kwargs)

    def create_session(self):
        connector = aiohttp.TCPConnector(verify_ssl=self.http_verify)

        return aiohttp.ClientSession(
            connector=connector,
            loop=self.loop,
            headers=self.http_headers,
            auth=self.http_auth)

    def _load_remote_data(self, url):

        @asyncio.coroutine
        def _load_remote_data_async():
            with aiohttp.Timeout(self.load_timeout):
                response = yield from self.session.get(url)
                result = yield from response.read()

            return result

        # Block until we have the data
        result = self.loop.run_until_complete(_load_remote_data_async())
        return result

    @asyncio.coroutine
    def post(self, address, message, headers):
        self.logger.debug("HTTP Post to %s:\n%s", address, message)
        with aiohttp.Timeout(self.operation_timeout):
            response = yield from self.session.post(
                address, data=message, headers=headers)
            self.logger.debug(
                "HTTP Response from %s (status: %d):\n%s",
                address, response.status, (yield from response.read()))
            return response

    @asyncio.coroutine
    def post_xml(self, address, envelope, headers):
        message = etree_to_string(envelope)
        response = yield from self.post(address, message, headers)

        from pretend import stub
        return stub(
            content=(yield from response.read()),
            status_code=response.status,
            headers=response.headers)

    @asyncio.coroutine
    def get(self, address, params, headers):
        with aiohttp.Timeout(self.operation_timeout):
            response = yield from self.session.get(
                address, params=params, headers=headers)

            from pretend import stub
            return (yield from stub(
                content=(yield from response.read()),
                status_code=response.status,
                headers=response.headers))
