========================
Zeep: Python SOAP client 
========================

A fast and modern Python SOAP client

Highlights:
 * Modern codebase compatible with Python 2.7, 3.3, 3.4, 3.5 and PyPy
 * Build on top of lxml and requests
 * Supports recursive WSDL and XSD documents.
 * Supports the xsd:choice and xsd:any elements.
 * Uses the defusedxml module for handling potential XML security issues
 * Support for WSSE (UsernameToken only for now)
 * Experimental support for HTTP bindings

Features still in development include:
 * WSSE x.509 support (BinarySecurityToken)
 * XML validation using lxml XMLSchema's
 * WS-Addressing and WS Policy support


Simple example::

    >>> from zeep import Client
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL')
    >>> print(client.service.ConvertSpeed(
    ...     100, 'kilometersPerhour', 'milesPerhour'))
    62.137


Quick Introduction
==================

Zeep inspects the wsdl document and generates the corresponding bindings.  This
provides an easy to use programmatic interface to a soap server.

The emphasis is on Soap 1.1 and Soap 1.2, however Zeep also offers experimental
support for HTTP Get and Post bindings.

Parsing the XML documents is done by using the lxml library. This is the most
performant and compliant Python XML library currently available. This results
in major speed benefits when retrieving large soap responses.


A simple use-case
-----------------

To give you an idea how zeep works a basic example.

.. code-block:: python

    import zeep

    wsdl = 'http://www.soapclient.com/xml/soapresponder.wsdl'
    client = zeep.Client(wsdl=wsdl)
    print(client.service.Method1('Zeep', 'is cool'))

The WSDL used above only defines one simple function (``Method1``) which is 
made available by zeep via ``client.service.Method1``. It takes two arguments
and returns a string. To get an overview of the services available on the 
endpoint you can run the following command in your terminal.

.. code-block:: bash

    python -mzeep http://www.soapclient.com/xml/soapresponder.wsdl



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





More information
================

.. toctree::
   :maxdepth: 1
   :name: mastertoc

   in-depth
   transport
   wsse
   helpers
   changes


Support
=======

If you encounter bugs then please `let me know`_ .  A copy of the WSDL file if
possible would be most helpful. 

I'm also able to offer commercial support.  Please contact me at
info@mvantellingen.nl for more information.


.. _let me know: https://github.com/mvantellingen/python-zeep/issues
