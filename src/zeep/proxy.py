import copy
import itertools
import logging

logger = logging.getLogger(__name__)


class OperationProxy:
    def __init__(self, service_proxy, operation_name):
        self._proxy = service_proxy
        self._op_name = operation_name

    @property
    def __doc__(self):
        return str(self._proxy._binding._operations[self._op_name])

    def _merge_soap_headers(self, operation_soap_headers):
        # Merge the default _soapheaders with the passed _soapheaders
        if self._proxy._client._default_soapheaders:
            if operation_soap_headers:
                soap_headers = copy.deepcopy(self._proxy._client._default_soapheaders)
                if type(soap_headers) != type(operation_soap_headers):
                    raise ValueError("Incompatible soapheaders definition")

                if isinstance(operation_soap_headers, list):
                    soap_headers.extend(operation_soap_headers)
                else:
                    soap_headers.update(operation_soap_headers)
            else:
                soap_headers = self._proxy._client._default_soapheaders
            return soap_headers

    def __call__(self, *args, **kwargs):
        """Call the operation with the given args and kwargs.

        :rtype: zeep.xsd.CompoundValue

        """
        kwargs['_soapheaders'] = self._merge_soap_headers(kwargs.get("_soapheaders"))

        return self._proxy._binding.send(
            self._proxy._client,
            self._proxy._binding_options,
            self._op_name,
            args,
            kwargs,
        )


class AsyncOperationProxy(OperationProxy):

    async def __call__(self, *args, **kwargs):
        """Call the operation with the given args and kwargs.

        :rtype: zeep.xsd.CompoundValue

        """
        kwargs['_soapheaders'] = self._merge_soap_headers(kwargs.get("_soapheaders"))

        return await self._proxy._binding.send_async(
            self._proxy._client,
            self._proxy._binding_options,
            self._op_name,
            args,
            kwargs,
        )


class ServiceProxy:
    def __init__(self, client, binding, **binding_options):
        self._client = client
        self._binding_options = binding_options
        self._binding = binding
        self._operations = {
            name: OperationProxy(self, name) for name in self._binding.all()
        }

    def __getattr__(self, key):
        """Return the OperationProxy for the given key.

        :rtype: OperationProxy()

        """
        return self[key]

    def __getitem__(self, key):
        """Return the OperationProxy for the given key.

        :rtype: OperationProxy()

        """
        try:
            return self._operations[key]
        except KeyError:
            raise AttributeError("Service has no operation %r" % key)

    def __iter__(self):
        """ Return iterator over the services and their callables. """
        return iter(self._operations.items())

    def __dir__(self):
        """ Return the names of the operations. """
        return list(itertools.chain(dir(super()), self._operations))


class AsyncServiceProxy(ServiceProxy):
    def __init__(self, client, binding, **binding_options):
        self._client = client
        self._binding_options = binding_options
        self._binding = binding
        self._operations = {
            name: AsyncOperationProxy(self, name) for name in self._binding.all()
        }
