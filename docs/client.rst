==================
The Client object
==================

.. currentmodule:: zeep

The :class:`Client` is the main interface for interacting with a SOAP server.
It provides a ``service`` attribute which references the default binding of
the client (via a :class:`ServiceProxy` object). The default binding can be specified
when initiating the client by passing the ``service_name`` and ``port_name``.
Otherwise the first service and first port within that service are used as the
default.


.. _client_cache:

Caching of WSDL and XSD files
------------------------------
When the client is initialized it will automatically retrieve the WSDL file
passed as argument. This WSDL file generally references various other WSDL and
XSD files. By default Zeep doesn't cache these files but it is however
advised to enable this for performance reasons.

Please see :ref:`transport_caching` how to enable this. To make it easy to
use the ``zeep.CachingClient()`` automatically creates a Transport object
with SqliteCache enabled.


Configuring the client
----------------------
The Client class accepts a settings argument to configuring the client. You can
initialise the object using the following code:


.. code-block:: python

    from zeep import Client, Settings

    settings = Settings(strict=False, xml_huge_tree=True)
    client = Client('http://my-wsdl/wsdl', settings=settings)


The settings object is always accessible via the client using
``client.settings``. For example:

.. code-block:: python

    with client.settings(raw_response=True):
        response = client.service.myoperation()

Please see :ref:`settings` for more information.


Strict mode
~~~~~~~~~~~
By default zeep will operate in 'strict' mode. This can be disabled if you
are working with a SOAP server which is not standards compliant by using the
strict setting. See :ref:`settings`. Disabling strict mode will change the
following behaviour:

 - The XML is parsed with the recover mode enabled
 - Nonoptional elements are allowed to be missing in xsd:sequences

Note that disabling strict mode should be considered a last resort since it
might result in data-loss between the XML and the returned response.


The ServiceProxy object
-----------------------

The ServiceProxy object is a simple object which will check if an operation
exists for attribute or item requested.  If the operation exists then it will
return an OperationProxy object (callable) which is responsible for calling the
operation on the binding.


.. code-block:: python

    from zeep import Client
    from zeep import xsd

    client = Client('http://my-endpoint.com/production.svc?wsdl')

    # service is a ServiceProxy object.  It will check if there
    # is an operation with the name `X` defined in the binding
    # and if that is the case it will return an OperationProxy
    client.service.X()

    # The operation can also be called via an __getitem__ call.
    # This is useful if the operation name is not a valid
    # python attribute name.
    client.service['X-Y']()


Using non-default bindings
--------------------------
As mentioned by default Zeep picks the first binding in the WSDL as the
default. This binding is available via ``client.service``. To use a specific
binding you can use the ``bind()`` method on the client object:


.. code-block:: python

    from zeep import Client
    from zeep import xsd

    client = Client('http://my-endpoint.com/production.svc?wsdl')

    service2 = client.bind('SecondService', 'Port12')
    service2.someOperation(myArg=1)


Creating new ServiceProxy objects
---------------------------------
There are situations where you either need to change the SOAP address from the
one which is defined within the WSDL or the WSDL doesn't define any service
elements. This can be done by creating a new ServiceProxy using the
``Client.create_service()`` method.

.. code-block:: python

    from zeep import Client
    from zeep import xsd

    client = Client('http://my-endpoint.com/production.svc?wsdl')
    service = client.create_service(
        '{http://my-target-namespace-here}myBinding',
        'http://my-endpoint.com/acceptance/')

    service.submit('something')


Creating the raw XML documents
------------------------------
When you want zeep to build and return the XML instead of sending it to the
server you can use the ``Client.create_message()`` call. It requires the
ServiceProxy as the first argument and the operation name as the second argument.


.. code-block:: python

    from zeep import Client

    client = Client('http://my-endpoint.com/production.svc?wsdl')
    node = client.create_message(client.service, 'myOperation', user='hi')
