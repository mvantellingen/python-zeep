class Plugin(object):
    """Base plugin"""

    def ingress(self, envelope, http_headers, operation):
        return envelope, http_headers

    def egress(self, envelope, http_headers, operation, binding_options):
        return envelope, http_headers


def apply_egress(client, envelope, http_headers, operation, binding_options):
    for plugin in client.plugins:
        envelope, http_headers = plugin.egress(
            envelope, http_headers, operation, binding_options)

    return envelope, http_headers


def apply_ingress(client, envelope, http_headers, operation):
    for plugin in client.plugins:
        envelope, http_headers = plugin.ingress(
            envelope, http_headers, operation)

    return envelope, http_headers
