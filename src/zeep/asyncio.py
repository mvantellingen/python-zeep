"""
Adds asyncio support to Zeep. Contains Python 3.5+ only syntax!

"""
import asyncio

import aiohttp

from zeep.transports import Transport
from zeep.wsdl import bindings
from zeep.wsdl.utils import etree_to_string


class AsyncTransport(Transport):
    supports_async = True

    def __init__(self, loop, *args, **kwargs):
        self.loop = loop if loop else asyncio.get_event_loop()
        super().__init__(*args, **kwargs)

        # Create a separate regular requests session for non async
        self._load_session = Transport.create_session(self)

    def create_session(self):
        connector = aiohttp.TCPConnector(verify_ssl=self.http_verify)

        return aiohttp.ClientSession(
            connector=connector,
            loop=self.loop,
            headers=self.http_headers,
            auth=self.http_auth)

    def _load_remote_data(self, url):
        response = self._load_session.get(url, timeout=self.load_timeout)
        response.raise_for_status()
        return response.content

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


class AsyncSoapBinding(object):

    async def send(self, client, options, operation, args, kwargs):
        envelope, http_headers = self._create(
            operation, args, kwargs,
            client=client,
            options=options)

        response = await client.transport.post_xml(
            options['address'], envelope, http_headers)

        operation_obj = self.get(operation)
        return self.process_reply(client, operation_obj, response)


class AsyncSoap11Binding(AsyncSoapBinding, bindings.Soap11Binding):
    pass


class AsyncSoap12Binding(AsyncSoapBinding, bindings.Soap12Binding):
    pass
