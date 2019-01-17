from inspect import iscoroutinefunction

async def apply_egress(client, envelope, http_headers, operation, binding_options):
    for plugin in client.plugins:
        if iscoroutinefunction(plugin.egress):
            result = await plugin.egress(
                envelope, http_headers, operation, binding_options)
        else:
            result = plugin.egress(
                envelope, http_headers, operation, binding_options)
        if result is not None:
            envelope, http_headers = result

    return envelope, http_headers


async def apply_ingress(client, envelope, http_headers, operation):
    for plugin in client.plugins:
        if iscoroutinefunction(plugin.ingress):
            result = await plugin.ingress(envelope, http_headers, operation)
        else:
            result = plugin.ingress(envelope, http_headers, operation)
        if result is not None:
            envelope, http_headers = result

    return envelope, http_headers
