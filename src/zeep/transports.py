import logging

import requests

from six.moves.urllib.parse import urlparse
from zeep.cache import SqliteCache
from zeep.utils import NotSet, get_version
from zeep.wsdl.utils import etree_to_string


class Transport(object):

    def __init__(self, cache=NotSet, timeout=300, verify=True, http_auth=None, **kwargs):
        self.extra_kwargs = kwargs
        self.cache = SqliteCache() if cache is NotSet else cache
        self.timeout = timeout
        self.verify = verify
        self.http_auth = http_auth
        self.logger = logging.getLogger(__name__)
        self.session = self.create_session()
        self.session.verify = verify
        self.session.auth = http_auth
        self.session.headers['User-Agent'] = (
            'Zeep/%s (www.python-zeep.org)' % (get_version()))

    def create_session(self, cert=None):
        _session = requests.Session()
        _session.cert = self.extra_kwargs.get('cert') or None
        return _session

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
        self.logger.debug("HTTP Post to %s:\n%s", address, message)
        response = self.session.post(address, data=message, headers=headers)
        self.logger.debug(
            "HTTP Response from %s (status: %d):\n%s",
            address, response.status_code, response.content)
        return response

    def post_xml(self, address, envelope, headers):
        """Post the envelope xml element to the given address with the headers.

        This method is intended to be overriden if you want to customize the
        serialization of the xml element. By default the body is formatted
        and encoded as utf-8. See ``zeep.wsdl.utils.etree_to_string``.

        """
        message = etree_to_string(envelope)
        return self.post(address, message, headers)

    def get(self, address, params, headers):
        response = self.session.get(address, params=params, headers=headers)
        return response