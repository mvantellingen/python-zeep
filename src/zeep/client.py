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


class Client(object):

    def __init__(self, wsdl, cache=None):
        self.cache = cache or SqliteCache()
        self.transport = Transport(self.cache)
        self.wsdl = WSDL(wsdl, self.transport)

    def call(self, name, *args, **kwargs):
        port = self.get_port()
        return port.send(self.transport, name, args, kwargs)

    def get_port(self, service=None, port=None):
        service = list(self.wsdl.services.values())[0]
        return list(service.ports.values())[0]
