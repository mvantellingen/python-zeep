import logging
import warnings

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
            self._proxy._client, self._op_name, args, kwargs)


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

    def __init__(self, wsdl, wsse=None, transport=None):
        self.transport = transport or Transport()
        self.wsdl = WSDL(wsdl, self.transport)
        self.wsse = wsse

        self.service = self.bind()

    def bind(self, service_name=None, port_name=None):
        """Create a new ServiceProxy for the given service_name and port_name

        The default ServiceProxy instance (`self.service`) always referes to
        the first service/port in the WSDL.  Use this when a specific port is
        required.

        """
        if service_name:
            service = self.wsdl.services.get(service_name)
            if not service:
                raise ValueError("Service not found")
        else:
            service = list(self.wsdl.services.values())[0]

        if port_name:
            port = service.ports.get(port_name)
            if not port:
                raise ValueError("Port not found")
        else:
            port = list(service.ports.values())[0]
        return ServiceProxy(self, port)

    def get_port(self, service=None, port=None):
        message = "This method will be removed in 0.6, please use bind()"
        warnings.warn(message, DeprecationWarning, stacklevel=1)

        service = list(self.wsdl.services.values())[0]
        return list(service.ports.values())[0]

    def get_type(self, name):
        return self.wsdl.schema.get_type(name)

    def get_element(self, name):
        return self.wsdl.schema.get_element(name)
