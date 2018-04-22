"""
Adds asyncio support to Zeep. Contains Python 3.5+ only syntax!

"""
import asyncio
import logging

import aiohttp
from requests import Response

from zeep.asyncio import bindings
from zeep.exceptions import TransportError
from zeep.transports import Transport
from zeep.utils import get_version
from zeep.wsdl.utils import etree_to_string

__all__ = ['AsyncTransport']


class AsyncTransport(Transport):
    """Asynchronous Transport class using aiohttp."""
    binding_classes = [
                bindings.AsyncSoap11Binding,
                bindings.AsyncSoap12Binding,
            ]

    def __init__(self, loop, cache=None, timeout=300, operation_timeout=None,
                 session=None):

        self.loop = loop if loop else asyncio.get_event_loop()
        self.cache = cache
        self.load_timeout = timeout
        self.operation_timeout = operation_timeout
        self.logger = logging.getLogger(__name__)

        self.session = session or aiohttp.ClientSession(loop=self.loop)
        self._close_session = session is None
        self.session._default_headers['User-Agent'] = (
            'Zeep/%s (www.python-zeep.org)' % (get_version()))

    def __del__(self):
        if self._close_session:
            self.session.connector.close()

    def _load_remote_data(self, url):
        result = None

        async def _load_remote_data_async():
            nonlocal result
            async with self.session.get(url, timeout=self.load_timeout) as response:
                result = await response.read()
                try:
                    response.raise_for_status()
                except aiohttp.ClientError as exc:
                    raise TransportError(
                        message=str(exc),
                        status_code=response.status,
                        content=result
                    ).with_traceback(exc.__traceback__) from exc

        # Block until we have the data
        self.loop.run_until_complete(_load_remote_data_async())
        return result

    async def post(self, address, message, headers):
        self.logger.debug("HTTP Post to %s:\n%s", address, message)
        async with self.session.post(address, data=message, headers=headers,
                                     timeout=self.operation_timeout) as response:
            self.logger.debug(
                "HTTP Response from %s (status: %d):\n%s",
                address, response.status, await response.read())
            return response

    async def post_xml(self, address, envelope, headers):
        message = etree_to_string(envelope)
        response = await self.post(address, message, headers)
        return await self.new_response(response)

    async def get(self, address, params, headers):
        async with self.session.get(address, params=params, headers=headers,
                                    timeout=self.operation_timeout) as response:

            return await self.new_response(response)

    async def new_response(self, response):
        """Convert an aiohttp.Response object to a requests.Response object"""
        new = Response()
        new._content = await response.read()
        new.status_code = response.status
        new.headers = response.headers
        new.cookies = response.cookies
        new.encoding = response.charset
        return new
