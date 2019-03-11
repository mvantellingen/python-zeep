from zeep.wsdl import bindings
from zeep import wsa
from zeep.asyncio import plugins

from requests_toolbelt.multipart.decoder import MultipartDecoder

from zeep.exceptions import Fault, TransportError, XMLSyntaxError
from zeep.loader import parse_xml
from zeep.utils import as_qname, get_media_type, qname_attr
from zeep.wsdl.attachments import MessagePack
from zeep.wsdl.messages.xop import process_xop

__all__ = ["AsyncSoap11Binding", "AsyncSoap12Binding"]


class AsyncSoapBinding(object):
    async def send(self, client, options, operation, args, kwargs):
        envelope, http_headers = await self._create(
            operation, args, kwargs, client=client, options=options
        )

        response = await client.transport.post_xml(
            options["address"], envelope, http_headers
        )

        if client.settings.raw_response:
            return response

        operation_obj = self.get(operation)
        return await self.process_reply(client, operation_obj, response)

    async def _create(self, operation, args, kwargs, client=None, options=None):
        """Create the XML document to send to the server.

        Note that this generates the soap envelope without the wsse applied.

        """
        operation_obj = self.get(operation)
        if not operation_obj:
            raise ValueError("Operation %r not found" % operation)

        # Create the SOAP envelope
        serialized = operation_obj.create(*args, **kwargs)
        self._set_http_headers(serialized, operation_obj)

        envelope = serialized.content
        http_headers = serialized.headers

        # Apply ws-addressing
        if client:
            if not options:
                options = client.service._binding_options

            if operation_obj.abstract.input_message.wsa_action:
                envelope, http_headers = wsa.WsAddressingPlugin().egress(
                    envelope, http_headers, operation_obj, options
                )

            # Apply plugins
            envelope, http_headers = await plugins.apply_egress(
                client, envelope, http_headers, operation_obj, options
            )

            # Apply WSSE
            if client.wsse:
                if isinstance(client.wsse, list):
                    for wsse in client.wsse:
                        envelope, http_headers = wsse.apply(envelope, http_headers)
                else:
                    envelope, http_headers = client.wsse.apply(envelope, http_headers)

        # Add extra http headers from the setings object
        if client.settings.extra_http_headers:
            http_headers.update(client.settings.extra_http_headers)

        return envelope, http_headers

    async def process_reply(self, client, operation, response):
        """Process the XML reply from the server.

        :param client: The client with which the operation was called
        :type client: zeep.client.Client
        :param operation: The operation object from which this is a reply
        :type operation: zeep.wsdl.definitions.Operation
        :param response: The response object returned by the remote server
        :type response: requests.Response

        """
        if response.status_code in (201, 202) and not response.content:
            return None

        elif response.status_code != 200 and not response.content:
            raise TransportError(
                u"Server returned HTTP status %d (no content available)"
                % response.status_code,
                status_code=response.status_code,
            )

        content_type = response.headers.get("Content-Type", "text/xml")
        media_type = get_media_type(content_type)
        message_pack = None

        # If the reply is a multipart/related then we need to retrieve all the
        # parts
        if media_type == "multipart/related":
            decoder = MultipartDecoder(
                response.content, content_type, response.encoding or "utf-8"
            )
            content = decoder.parts[0].content
            if len(decoder.parts) > 1:
                message_pack = MessagePack(parts=decoder.parts[1:])
        else:
            content = response.content

        try:
            doc = parse_xml(content, self.transport, settings=client.settings)
        except XMLSyntaxError as exc:
            raise TransportError(
                "Server returned response (%s) with invalid XML: %s.\nContent: %r"
                % (response.status_code, exc, response.content),
                status_code=response.status_code,
                content=response.content,
            )

        # Check if this is an XOP message which we need to decode first
        if message_pack:
            if process_xop(doc, message_pack):
                message_pack = None

        if client.wsse:
            client.wsse.verify(doc)

        doc, http_headers = await plugins.apply_ingress(
            client, doc, response.headers, operation
        )

        # If the response code is not 200 or if there is a Fault node available
        # then assume that an error occured.
        fault_node = doc.find("soap-env:Body/soap-env:Fault", namespaces=self.nsmap)
        if response.status_code != 200 or fault_node is not None:
            return self.process_error(doc, operation)

        result = operation.process_reply(doc)

        if message_pack:
            message_pack._set_root(result)
            return message_pack
        return result

class AsyncSoap11Binding(AsyncSoapBinding, bindings.Soap11Binding):
    pass


class AsyncSoap12Binding(AsyncSoapBinding, bindings.Soap12Binding):
    pass
