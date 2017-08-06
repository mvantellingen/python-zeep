"""
Adds async tornado.gen support to Zeep.

"""
import logging
import urllib
import tornado.ioloop
from tornado import gen, httpclient
from requests import Response, Session
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from zeep.transports import Transport
from zeep.utils import get_version
from zeep.wsdl.utils import etree_to_string

__all__ = ['TornadoAsyncTransport']


class TornadoAsyncTransport(Transport):
    """Asynchronous Transport class using tornado gen."""
    supports_async = True

    def __init__(self, loop, cache=None, timeout=300, operation_timeout=None,
                 session=None):

        self.loop = loop if loop else tornado.ioloop.IOLoop.instance()
        self.cache = cache
        self.load_timeout = timeout
        self.operation_timeout = operation_timeout
        self.logger = logging.getLogger(__name__)

        self.session = session or Session()
        self.session.headers['User-Agent'] = (
            'Zeep/%s (www.python-zeep.org)' % (get_version()))

    def _load_remote_data(self, url):
        @gen.coroutine
        def _load_remote_data_async():
            async_client = httpclient.AsyncHTTPClient()
            kwargs = {'method': 'GET'}
            http_req = httpclient.HTTPRequest(url, **kwargs)
            response = yield async_client.fetch(http_req)
            raise gen.Return(self.new_response(response))

        return self.loop.run_sync(_load_remote_data_async())

    @gen.coroutine
    def post(self, address, message, headers):
        async_client = httpclient.AsyncHTTPClient()

        # extracting auth
        auth_username = None
        auth_password = None
        auth_mode = None

        if self.session.auth is not None:
            if type(self.session.auth) is tuple:
                auth_username = self.session.auth[0]
                auth_password = self.session.auth[1]
                auth_mode = 'basic'
            elif type(self.session.auth) is HTTPBasicAuth:
                auth_username = self.session.username
                auth_password = self.session.password
                auth_mode = 'basic'
            elif type(self.session.auth) is HTTPDigestAuth:
                auth_username = self.session.username
                auth_password = self.session.password
                auth_mode = 'digest'
            else:
                raise StandardError('Not supported authentication.')

        # extracting client cert
        client_cert = None
        client_key = None

        if self.session.cert is not None:
            if type(self.session.cert) is str:
                client_cert = self.session.cert
            elif type(self.session.cert) is tuple:
                client_cert = self.session.cert[0]
                client_key = self.session.cert[1]

        kwargs = {
            'method': 'POST',
            'request_timeout': self.timeout,
            'headers': headers + self.session.headers,
            'auth_username': auth_username,
            'auth_password': auth_password,
            'auth_mode': auth_mode,
            'validate_cert': self.sessionverify,
            'client_key': client_key,
            'client_cert': client_cert,
            'body': message
        }

        http_req = httpclient.HTTPRequest(address, **kwargs)
        response = yield async_client.po(http_req)

        raise gen.Return(self.new_response(response))

    @gen.coroutine
    def post_xml(self, address, envelope, headers):
        message = etree_to_string(envelope)

        response = yield self.post(address, message, headers)

        raise gen.Return(self.new_response(response))

    @gen.coroutine
    def get(self, address, params, headers):
        async_client = httpclient.AsyncHTTPClient()
        if params:
            address += '?' + urllib.urlencode(params)

        # extracting auth
        auth_username = None
        auth_password = None
        auth_mode = None

        if self.session.auth is not None:
            if type(self.session.auth) is tuple:
                auth_username = self.session.auth[0]
                auth_password = self.session.auth[1]
                auth_mode = 'basic'
            elif type(self.session.auth) is HTTPBasicAuth:
                auth_username = self.session.username
                auth_password = self.session.password
                auth_mode = 'basic'
            elif type(self.session.auth) is HTTPDigestAuth:
                auth_username = self.session.username
                auth_password = self.session.password
                auth_mode = 'digest'
            else:
                raise StandardError('Not supported authentication.')

        # extracting client cert
        client_cert = None
        client_key = None

        if self.session.cert is not None:
            if type(self.session.cert) is str:
                client_cert = self.session.cert
            elif type(self.session.cert) is tuple:
                client_cert = self.session.cert[0]
                client_key = self.session.cert[1]

        kwargs = {
            'method': 'GET',
            'request_timeout': self.timeout,
            'headers': headers + self.session.headers,
            'auth_username': auth_username,
            'auth_password': auth_password,
            'auth_mode': auth_mode,
            'validate_cert': self.sessionverify,
            'client_key': client_key,
            'client_cert': client_cert


        }

        http_req = httpclient.HTTPRequest(address, **kwargs)
        response = yield async_client.fetch(http_req)

        raise gen.Return(self.new_response(response))

    def new_response(self, response):
        """Convert an tornado.HTTPResponse object to a requests.Response object"""
        new = Response()
        new._content = response.body
        new.status_code = response.code
        new.headers = response.headers # seems that headers may be in a wrong format here
        # new.cookies = response.cookies
        # new.encoding = response.charset
        return new