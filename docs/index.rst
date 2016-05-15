========================
Zeep: Python SOAP client 
========================

A fast and hip Python SOAP client ;-)

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


A quick example::

    >>> from zeep import Client
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL')
    >>> print client.service.ConvertSpeed(
    ...     100, 'kilometersPerhour', 'milesPerhour')
    62.137



Complex requests
================

Most of the times you need to pass nested data to the soap client.  These 
Complex types can be created using the `client.get_type()` method::

    >>> from zeep import Client
    >>> client = Client('http://my-entrprisy-endpoint.com')
    >>> order_type = client.get_type('ns0:Order')
    >>> order = order_type(
    ...     number='1234', billing_address=billing_address)
    >>> client.service.submit_order(user_id=1, order=order)


Any objects
===========

Zeep offers proper support for Any elements. 

    >>> from zeep import Client
    >>> from zeep import xsd
    >>> client = Client('http://my-entrprisy-endpoint.com')
    >>> order_type = client.get_element('ns0:Order')
    >>> order = xsd.AnyObject(
    ...     order_type, 
    ...     order_type(number='1234', billing_address=billing_address))
    >>> client.service.submit_something(user_id=1, _any_1=order)


WS-Security (WSSE)
==================
Only the UsernameToken profile is supported for now.  It supports both the 
passwordText and passwordDigest methods::

    >>> from zeep import Client
    >>> from zeep.wsse.username import UsernameToken
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL', 
    ...     wsse=UsernameToken('username', 'password'))

To use the passwordDigest method you need to supply `use_digest=True` to the
`UsernameToken` class.


Caching
=======
The default cache backed is SqliteCache.  It caches the WSDL and XSD files for 
1 hour by default. You can disable caching by passing `None` as value to the
`Transport.cache` attribute when initializing the client::

    >>> from zeep import Client
    >>> from zeep.cache import SqliteCache
    >>> from zeep.transports import Transport
    >>> transport = Transport(cache=None)
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL', 
    ...     transport=transport)


Changing the SqliteCache settings can be done via::


    >>> from zeep import Client
    >>> from zeep.cache import SqliteCache
    >>> from zeep.transports import Transport
    >>> cache = SqliteCache(persistent=True, timeout=60)
    >>> transport = Transport(cache=cache)
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
    ...     transport=transport)


Transport options
=================
If you need to change options like cache, timeout or ssl verification
use `Transport` class.

For instance to disable SSL verification use `verify` option::

    >>> from zeep import Client
    >>> from zeep.transports import Transport
    >>> transport = Transport(verify=False)
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
    ...     transport=transport)


Helpers
=======
In the `zeep.helper` module the following helpers functions are available:

   - `serialize_object()` - Convert zeep value objects to native python 
     datastructures.

Bugs
====

If you encounter bugs then please `let me know`_ .  A copy of the WSDL file if
possible would be most helpful. If you are really cool then please open a PR
with the fix... :P


.. _let me know: https://github.com/mvantellingen/python-zeep/issues


Contributing
============

Contributions are welcome!


Changelog
=========

.. include:: ../CHANGES
