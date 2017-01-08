
import os
import re
import logging
import requests_toolbelt
from contextlib import contextmanager

import requests

from six.moves.urllib.parse import urlparse
from zeep.cache import SqliteCache
from zeep.utils import NotSet, get_version
from zeep.wsdl.utils import etree_to_string


def multipart_log_message(response):
    """Return a log message of the multipart response content, including headers
    If the content is not text/xml, return only a byte count

    :param response: response object from requests session
    :return: log message for use in debug output
    """
    log_message = "\n".join([a + ": " + b for a, b in response.headers.items()])
    multipart = requests_toolbelt.multipart.decoder.MultipartDecoder.from_response(response)
    for part in multipart.parts:
        log_message += "\n\n--%s\n%s" % (
        multipart.boundary.decode(),
        # The requests_toolbelt multipart decoder returns headers in binary format, need to decode
        "\n".join([a.decode() + ": " + b.decode() for a, b in part.headers.items()]))
        if b'Content-Type' in part.headers:
            m = re.match("text/xml(; charset=(\S+))?", part.headers[b'Content-type'].decode())
            if m:
                charset = m.group(2)
                if not charset:
                    charset = 'utf-8'
                log_message += "\n\n%s" % part.content.decode(charset)
            else:
                log_message += "\n\n ... %s bytes of data ...\n--%s--" % (
                len(part.content), multipart.boundary.decode())
    return log_message


class Transport(object):
    """The transport object handles all communication to the SOAP server.

    :param cache: The cache object to be used to cache GET requests
    :param timeout: The timeout for loading wsdl and xsd documents.
    :param operation_timeout: The timeout for operations (POST/GET). By
                              default this is None (no timeout).
    :param verify: Boolean to indicate if the SSL certificate needs to be
                   verified.
    :param http_auth: HTTP authentication, passed to requests.

    """
    supports_async = False

    def __init__(self, cache=NotSet, timeout=300, operation_timeout=None,
                 verify=True, http_auth=None):
        self.cache = SqliteCache() if cache is NotSet else cache
        self.load_timeout = timeout
        self.operation_timeout = operation_timeout
        self.logger = logging.getLogger(__name__)

        self.http_verify = verify
        self.http_auth = http_auth
        self.http_headers = {
            'User-Agent': 'Zeep/%s (www.python-zeep.org)' % (get_version())
        }
        self.session = self.create_session()

    def create_session(self):
        session = requests.Session()
        session.verify = self.http_verify
        session.auth = self.http_auth
        session.headers = self.http_headers
        return session

    def get(self, address, params, headers):
        """Proxy to requests.get()

        :param address: The URL for the request
        :param params: The query parameters
        :param headers: a dictionary with the HTTP headers.

        """
        response = self.session.get(
            address,
            params=params,
            headers=headers,
            timeout=self.operation_timeout)
        return response

    def post(self, address, message, headers):
        """Proxy to requests.posts()

        :param address: The URL for the request
        :param message: The content for the body
        :param headers: a dictionary with the HTTP headers.

        """
        if self.logger.isEnabledFor(logging.DEBUG):
            log_message = message
            if isinstance(log_message, bytes):
                log_message = log_message.decode('utf-8')
            self.logger.debug("HTTP Post to %s:\n%s", address, log_message)

        response = self.session.post(
            address,
            data=message,
            headers=headers,
            timeout=self.operation_timeout)

        if self.logger.isEnabledFor(logging.DEBUG):
            if "Content-Type" in response.headers:
                if re.match("multipart", response.headers["Content-Type"]):
                    log_message = multipart_log_message(response)
                else:
                    log_message = response.content
            if isinstance(log_message, bytes):
                log_message = log_message.decode('utf-8')

            self.logger.debug(
                "HTTP Response from %s (status: %d):\n%s",
                address, response.status_code, log_message)

        return response

    def post_xml(self, address, envelope, headers):
        """Post the envelope xml element to the given address with the headers.

        This method is intended to be overriden if you want to customize the
        serialization of the xml element. By default the body is formatted
        and encoded as utf-8. See ``zeep.wsdl.utils.etree_to_string``.

        """
        message = etree_to_string(envelope)
        return self.post(address, message, headers)

    def load(self, url):
        """Load the content from the given URL"""
        if not url:
            raise ValueError("No url given to load")

        scheme = urlparse(url).scheme
        if scheme in ('http', 'https'):

            if self.cache:
                response = self.cache.get(url)
                if response:
                    return bytes(response)

            content = self._load_remote_data(url)

            if self.cache:
                self.cache.add(url, content)

            return content

        elif scheme == 'file':
            if url.startswith('file://'):
                url = url[7:]

        with open(os.path.expanduser(url), 'rb') as fh:
            return fh.read()

    def _load_remote_data(self, url):
        response = self.session.get(url, timeout=self.load_timeout)
        response.raise_for_status()
        return response.content

    @contextmanager
    def _options(self, timeout=None):
        """Context manager to temporarily overrule options.

        Example::

            client = zeep.Client('foo.wsdl')
            with client.options(timeout=10):
                client.service.fast_call()

        :param timeout: Set the timeout for POST/GET operations (not used for
                        loading external WSDL or XSD documents)

        """
        old_timeout = self.operation_timeout
        self.operation_timeout = timeout
        yield
        self.operation_timeout = old_timeout
