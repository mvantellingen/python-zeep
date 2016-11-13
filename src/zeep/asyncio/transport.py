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
        result = None
        async def _load_remote_data_async():
            nonlocal result
            with aiohttp.Timeout(self.load_timeout):
                response = await self.session.get(url)
                result = await response.read()

        # Block until we have the data
        self.loop.run_until_complete(_load_remote_data_async())
        return result

    async def post(self, address, message, headers):
        self.logger.debug("HTTP Post to %s:\n%s", address, message)
        with aiohttp.Timeout(self.operation_timeout):
            response = await self.session.post(
                address, data=message, headers=headers)
            self.logger.debug(
                "HTTP Response from %s (status: %d):\n%s",
                address, response.status, await response.read())
            return response

    async def post_xml(self, address, envelope, headers):
        message = etree_to_string(envelope)
        response = await self.post(address, message, headers)

        from pretend import stub
        return stub(
            content=await response.read(),
            status_code=response.status,
            headers=response.headers)

    async def get(self, address, params, headers):
        with aiohttp.Timeout(self.operation_timeout):
            response = await self.session.get(
                address, params=params, headers=headers)

            from pretend import stub
            return await stub(
                content=await response.read(),
                status_code=response.status,
                headers=response.headers)
