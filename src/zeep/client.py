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
        return self._proxy._binding.send(
            self._proxy._client, self._proxy._binding_options,
            self._op_name, args, kwargs)


class ServiceProxy(object):
    def __init__(self, client, binding, **binding_options):
        self._client = client
        self._binding_options = binding_options
        self._binding = binding

    def __getattr__(self, key):
        return self[key]

    def __getitem__(self, key):
        try:
            self._binding.get(key)
        except KeyError:
            raise AttributeError('Service has no operation %r' % key)
        return OperationProxy(self, key)


class Client(object):

    def __init__(self, wsdl, wsse=None, transport=None,
                 service_name=None, port_name=None, plugins=None):
        if not wsdl:
            raise ValueError("No URL given for the wsdl")

        self.transport = transport or Transport()
        self.wsdl = Document(wsdl, self.transport)
        self.wsse = wsse
        self.plugins = plugins if plugins is not None else []

        self._default_service = None
        self._default_service_name = service_name
        self._default_port_name = port_name

    @property
    def service(self):
        """The default ServiceProxy instance"""
        if self._default_service:
            return self._default_service

        self._default_service = self.bind(
            service_name=self._default_service_name,
            port_name=self._default_port_name)
        if not self._default_service:
            raise ValueError(
                "There is no default service defined. This is usually due to "
                "missing wsdl:service definitions in the WSDL")
        return self._default_service

    def bind(self, service_name=None, port_name=None):
        """Create a new ServiceProxy for the given service_name and port_name.

        The default ServiceProxy instance (`self.service`) always referes to
        the first service/port in the wsdl Document.  Use this when a specific
        port is required.

        """
        if not self.wsdl.services:
            return

        if service_name:
            service = self.wsdl.services.get(service_name)
            if not service:
                raise ValueError("Service not found")
        else:
            service = next(iter(self.wsdl.services.values()), None)

        if port_name:
            port = service.ports.get(port_name)
            if not port:
                raise ValueError("Port not found")
        else:
            port = list(service.ports.values())[0]
        return ServiceProxy(self, port.binding, **port.binding_options)

    def create_service(self, binding_name, address):
        """Create a new ServiceProxy for the given binding name and address.

        :param binding_name: The QName of the binding
        :param address: The address of the endpoint

        """
        try:
            binding = self.wsdl.bindings[binding_name]
        except KeyError:
            raise ValueError(
                "No binding found with the given QName. Available bindings "
                "are: %s" % (', '.join(self.wsdl.bindings.keys())))
        return ServiceProxy(self, binding, address=address)

    def get_type(self, name):
        return self.wsdl.types.get_type(name)

    def get_element(self, name):
        return self.wsdl.types.get_element(name)
