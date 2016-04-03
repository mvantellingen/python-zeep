import logging

from zeep.cache import SqliteCache
from zeep.transports import Transport
from zeep.wsdl import WSDL

NSMAP = {
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
}


logger = logging.getLogger(__name__)


class OperationProxy(object):
    def __init__(self, service_proxy, operation_name):
        self._proxy = service_proxy
        self._op_name = operation_name

    def __call__(self, *args, **kwargs):
        return self._proxy._port.send(
            self._proxy._client.transport, self._op_name, args, kwargs)


class ServiceProxy(object):
    def __init__(self, client, port):
        self._client = client
        self._port = port
        self._binding = port.binding

    def __getattr__(self, key):
        try:
            self._binding.get(key)
        except KeyError:
            raise AttributeError('Service has no operation %r' % key)
        return OperationProxy(self, key)


class Client(object):

    def __init__(self, wsdl, cache=None):
        self.cache = cache or SqliteCache()
        self.transport = Transport(self.cache)
        self.wsdl = WSDL(wsdl, self.transport)

        port = self.get_port()
        self.service = ServiceProxy(self, port)

    def get_port(self, service=None, port=None):
        service = list(self.wsdl.services.values())[0]
        return list(service.ports.values())[0]

    def get_type(self, name):
        return self.wsdl.schema.get_type(name)

    def get_element(self, name):
        return self.wsdl.schema.get_element(name)
