========
In depth
========

WSDL documents provide a number of operations (functions) per binding. A 
binding is collection of operations which are called via a specific protocol.

These protocols are generally Soap 1.1 or Soap 1.2. As mentioned before Zeep
also offers experimental support for the Http Get and Http Post bindings. Most
of the time this is an implementation detail, Zeep should offer the same API
to the user independent of the underlying protocol.

One of the first things you will do if you start developing an interface to a
wsdl webservice is to get an overview of all available operations and there
call signatures. Zeep offers a command line interface to make this easy.


.. code-block:: bash

    python -mzeep http://www.soapclient.com/xml/soapresponder.wsdl

See ``python -mzeep --help`` for more information.


Non-default bindings
--------------------
By default zeep picks the first binding in the wsdl as the default. This 
binding is availble via ``client.service``. To use a specific binding you can
use ``binding = client.bind('MyService', 'MyPort')``. 


Overriding the default endpoint address
---------------------------------------
There are situations where you need to change the soap address from the one
which is defined within the WSDL. This can be done by using the
``Client.set_address()`` method.

.. code-block:: python

    from zeep import Client
    from zeep import xsd

    client = Client('http://my-endpoint.com/production.svc?wsdl')
    client.set_address(
        'EnterpriseService', 'EnterpriseSoap11', 
        'http://my-endpoint.com/acceptance/')
    client.service.submit('something')


Any objects
-----------

Zeep offers full support for xsd:any elements.

.. code-block:: python

    from zeep import Client
    from zeep import xsd

    client = Client('http://my-entrprisy-endpoint.com')
    order_type = client.get_element('ns0:Order')
    order = xsd.AnyObject(
      order_type, order_type(number='1234', price=99))
    client.service.submit_something(user_id=1, _any_1=order)

