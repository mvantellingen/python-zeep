from collections import deque


class Plugin(object):
    """Base plugin"""

    def ingress(self, envelope, http_headers, operation):
        return envelope, http_headers

    def egress(self, envelope, http_headers, operation, binding_options, *args, **kwargs):
        return envelope, http_headers


def apply_egress(client, envelope, http_headers, operation, binding_options, *args, **kwargs):
    for plugin in client.plugins:
        result = plugin.egress(
            envelope, http_headers, operation, binding_options, *args, **kwargs)
        if result is not None:
            envelope, http_headers = result

    return envelope, http_headers


def apply_ingress(client, envelope, http_headers, operation):
    for plugin in client.plugins:
        result = plugin.ingress(envelope, http_headers, operation)
        if result is not None:
            envelope, http_headers = result

    return envelope, http_headers


class HistoryPlugin(object):
    def __init__(self, maxlen=1):
        self._buffer = deque([], maxlen)

    @property
    def last_sent(self):
        last_tx = self._buffer[-1]
        if last_tx:
            return last_tx['sent']

    @property
    def last_received(self):
        last_tx = self._buffer[-1]
        if last_tx:
            return last_tx['received']

    def ingress(self, envelope, http_headers, operation):
        last_tx = self._buffer[-1]
        last_tx['received'] = {
            'envelope': envelope,
            'http_headers': http_headers,
        }

    def egress(self, envelope, http_headers, operation, binding_options, *args, **kwargs):
        self._buffer.append({
            'received': None,
            'sent': {
                'envelope': envelope,
                'http_headers': http_headers,
            },
        })
