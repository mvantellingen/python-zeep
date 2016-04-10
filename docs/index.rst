========================
Zeep: Python SOAP client 
========================

A fast and hip Python SOAP client ;-)


Highlights:
 * Modern codebase compatible with Python 2.7, 3.3, 3.4 and 3.5
 * Build on top of lxml and requests
 * Supports recursive WSDL and XSD documents and xsd:any elements.


Features still in development include:
 * Support for WSSE 
 * Support for HTTP bindings 
 * XML validation using lxml XMLSchema's


A quick example::

    >>> from zeep import Client
    >>> client = zeep.Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL')
    >>> print client.service.ConvertSpeed(
    ...     100, 'kilometersPerhour', 'milesPerhour')
    62.137



Complex requests
================

Most of the times you need to pass nested data to the soap client. These 
Complex types can be created using the `client.get_element()` method::

    >>> from zeep import Client
    >>> client = zeep.Client('http://my-entrprisy-endpoint.com')
    >>> order_type = client.get_element('ns0:Order')
    >>> order = order_type(
    ...     number='1234', billing_address=billing_address)
    >>> client.service.submit_order(user_id=1, order=order)



Any objects
===========

Zeep offers proper support for Any elements. 

    >>> from zeep import Client
    >>> from zeep import xsd
    >>> client = zeep.Client('http://my-entrprisy-endpoint.com')
    >>> order_type = client.get_element('ns0:Order')
    >>> order = xsd.AnyObject(
    ...     order_type, 
    ...     order_type(number='1234', billing_address=billing_address))
    >>> client.service.submit_something(user_id=1, _any_1=order)


Caching
=======
The default cache backed is SqliteCache. It caches the WSDL and XSD files for 
1 hour by default. You can disable caching by passing `None` as value to the
`cache` attribute when initializing the client::

    >>> from zeep import Client
    >>> from zeep.cache import SqliteCache
    >>> client = zeep.Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL', 
    ...     cache=None)


Changing the SqliteCache settings can be done via::


    >>> from zeep import Client
    >>> from zeep.cache import SqliteCache
    >>> client = zeep.Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
    ...     cache=SqliteCache(persistent=True, timeout=60))


Helpers
=======
In the `zeep.helper` module the following helpers functions are available:

   - `serialize_object()` - Convert zeep value objects to native python 
     datastructures.

Bugs
====

**Yes there will be bugs! :-)**

If you encounter bugs then please `let me know`_ . A copy of the WSDL file if
possible would be most helpful. If you are really cool then please open a PR
with the fix... :P


.. _let me know: https://github.com/mvantellingen/python-zeep/issues


Contributing
============

Contributions are welcome!


Changelog
=========

.. include:: ../CHANGES
