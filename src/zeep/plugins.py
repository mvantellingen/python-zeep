class Plugin(object):

    def ingress(self, envelope, http_headers):
        return envelope, http_headers

    def egress(self, envelope, http_headers):
        return envelope, http_headers


def apply_egress(client, envelope, http_headers):
    for plugin in client.plugins:
        envelope, http_headers = plugin.egress(envelope, http_headers)

    return envelope, http_headers


def apply_ingress(client, envelope, http_headers):
    for plugin in client.plugins:
        envelope, http_headers = plugin.ingress(envelope, http_headers)

    return envelope, http_headers
