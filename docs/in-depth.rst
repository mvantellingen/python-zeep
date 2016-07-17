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


Creating new service objects
----------------------------
There are situations where you either need to change the soap address from the
one which is defined within the WSDL or the WSDL doesn't define any service
elements. This can be done by using the ``Client.create_service()`` method.

.. code-block:: python

    from zeep import Client
    from zeep import xsd

    client = Client('http://my-endpoint.com/production.svc?wsdl')
    service = client.create_service(
        '{http://my-target-namespace-here}myBinding',
        'http://my-endpoint.com/acceptance/')
    service.submit('something')


Using SOAP headers
------------------
SOAP headers are generally used for things like authentication. The header
elements can be passed to all operations using the ``_soapheaders`` kwarg.

There are multiple ways to pass a value to the soapheader.

1. When the soap header expects a complex type you can either pass a dict or
   an object created via the ``client.get_element()`` method.
2. When the header expects a simple type value you can pass it directly to the
   ``_soapheaders`` kwarg. (e.g.: ``client.service.Method(_soapheader=1234)``)
3. Creating custom xsd element objects. For example::

    from zeep import xsd

    header = xsd.Element(
        '{http://test.python-zeep.org}auth',
        xsd.ComplexType([
            xsd.Element(
                '{http://test.python-zeep.org}username', 
                xsd.String()),
        ])
    )
    header_value = header(username='mvantellingen')
    client.service.Method(_soapheaders=[header_value])

4. Another option is to pass an lxml Element object. This is generally useful
   if the wsdl doesn't define a soap header but the server does expect it. 


xsd:choice
----------
Mapping the semantics of xsd:choice elements to code is unfortunately pretty
difficult. Zeep tries to solve this using two methods:

  1. Accepting the elements in the xsd:choice element as kwargs. This only 
     works for simple xsd:choice definitions.
  2. Using the special kwarg ``_value_N`` where the N is the number of the
     choice in the parent type. This method allows you to pass a list of 
     dicts (when maxOccurs != 1) or a dict directly.


The following examples should illustrate this better.



Simple method
~~~~~~~~~~~~~

.. code-block:: xml

    <?xml version="1.0"?>
    <schema xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/">
      <element name='ElementName'>
        <complexType xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <choice>
            <element name="item_1" type="string"/>
            <element name="item_2" type="string"/>
          </choice>
        </complexType>
      </element>
    </schema>


.. code-block:: python

    element = client.get_element('ns0:ElementName')
    obj = element(item_1='foo')


Nested using _value_1
~~~~~~~~~~~~~~~~~~~~~
.. code-block:: xml

    <?xml version="1.0"?>
    <schema xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/">
      <element name='ElementName'>
        <complexType xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <choice maxOccurs="unbounded">
            <sequence>
                <element name="item_1_a" type="string"/>
                <element name="item_1_b" type="string"/>
            </sequence>
            <element name="item_2" type="string"/>
          </choice>
        </complexType>
      </element>
    </schema>


.. code-block:: python

    element = client.get_element('ns0:ElementName')
    obj = element(_value_1={'item_1_a': 'foo', 'item_1_b': 'bar'})


Nested list using _value_1
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: xml

    <?xml version="1.0"?>
    <schema xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/">
      <element name='ElementName'>
        <complexType xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <choice maxOccurs="unbounded">
            <element name="item_1" type="string"/>
            <element name="item_2" type="string"/>
          </choice>
        </complexType>
      </element>
    </schema>


.. code-block:: python

    element = client.get_element('ns0:ElementName')
    obj = element(_value_1=[{'item_1': 'foo'}, {'item_2': 'bar'})


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
    client.service.submit_something(user_id=1, _value_1=order)

