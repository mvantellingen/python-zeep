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



xsd:choice
----------
Mapping the semantics of xsd:choice elements to code is unfortunately pretty
difficult. Zeep tries to solve this using two methods:

  1. Accepting the elements in the xsd:choice element as kwargs. This only 
     works for simple xsd:choice definitions.
  2. Using the special kwarg ``_choice_x`` where the x is the number of the
     choice in the parent type. This method allows you to pass a list of 
     dicts (when maxOccurs != 1) or a dict directly.


The following examples should better illustrate this.



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


Nested using _choice_1
~~~~~~~~~~~~~~~~~~~~~~
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
    obj = element(_choice_1={'item_1_a': 'foo', 'item_1_b': 'bar'})


Nested list using _choice_1
~~~~~~~~~~~~~~~~~~~~~~~~~~~
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
    obj = element(_choice_1=[{'item_1': 'foo'}, {'item_2': 'bar'})


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

