import logging

from zeep.transports import Transport
from zeep.wsdl import Document

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

    def __init__(self, wsdl, wsse=None, transport=None,
                 service_name=None, port_name=None):
        if not wsdl:
            raise ValueError("No URL given for the wsdl")

        self.transport = transport or Transport()
        self.wsdl = Document(wsdl, self.transport)
        self.wsse = wsse
        self.service = self.bind(service_name=service_name, port_name=port_name)

    def bind(self, service_name=None, port_name=None):
        """Create a new ServiceProxy for the given service_name and port_name

        The default ServiceProxy instance (`self.service`) always referes to
        the first service/port in the wsdl Document.  Use this when a specific
        port is required.

        """
        if not self.wsdl.services:
            raise ValueError(
                "No services found in the WSDL. Are you using the correct URL?")

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

    def set_address(self, service_name, port_name, address):
        """Override the default port address for the given `service_name`
        `port_name` combination.

        :param service_name: Name of the service
        :type address: string
        :param port_name: Name of the port within the service
        :type address: string
        :param address: URL of the server
        :type address: string

        """
        service = self.wsdl.services.get(service_name)
        if not service:
            raise ValueError("Service not found")

        port = service.ports.get(port_name)
        if not port:
            raise ValueError("Port not found")

        port.binding_options['address'] = address

    def get_type(self, name):
        return self.wsdl.schema.get_type(name)

    def get_element(self, name):
        return self.wsdl.schema.get_element(name)

    def last_sent(self):
        return self.transport.last_sent()

    def last_received(self):
        return self.transport.last_received()
