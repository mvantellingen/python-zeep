==============
Datastructures
==============

Nested objects
--------------

Most of the times you need to pass nested data to the soap client.  These 
Complex types can be created using the `client.get_type()` method.

.. code-block:: python

    from zeep import Client

    client = Client('http://my-enterprise-endpoint.com')
    order_type = client.get_type('ns0:Order')
    order = order_type(number='1234', price=99)
    client.service.submit_order(user_id=1, order=order)


However instead of creating an object from a type defined in the XSD you can
also pass in a dictionary. Zeep will automatically convert this dict to the
required object during the call.


.. code-block:: python

    from zeep import Client

    client = Client('http://my-enterprise-endpoint.com')
    client.service.submit_order(user_id=1, order={
        'number': '1234',
        'price': 99,
    })


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
