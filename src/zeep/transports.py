import requests
from six.moves.urllib.parse import urlparse

from zeep.cache import SqliteCache
from zeep.utils import NotSet


class Transport(object):

    def __init__(self, cache=NotSet, timeout=300, verify=True, http_auth=None):
        self.cache = SqliteCache() if cache is NotSet else cache
        self.timeout = timeout
        self.verify = verify
        self.http_auth = http_auth

        self.session = self.create_session()
        self.session.verify = verify
        self.session.auth = http_auth
        self._sent = None
        self._received = None

    def create_session(self):
        return requests.Session()

    def load(self, url):
        if not url:
            raise ValueError("No url given to load")

        scheme = urlparse(url).scheme
        if scheme in ('http', 'https'):

            if self.cache:
                response = self.cache.get(url)
                if response:
                    return bytes(response)

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            if self.cache:
                self.cache.add(url, response.content)

            return response.content

        elif scheme == 'file':
            if url.startswith('file://'):
                url = url[7:]

        with open(url, 'rb') as fh:
            return fh.read()

    def post(self, address, message, headers):
        self._sent = message
        response = self.session.post(address, data=message, headers=headers)
        self._received = response.content
        return response

    def get(self, address, params, headers):
        response = self.session.get(address, params=params, headers=headers)
        self._received = response.content
        return response

    def last_sent(self):
        return self._sent

    def last_received(self):
        return self._received
