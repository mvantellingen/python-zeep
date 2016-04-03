.. Zeep documentation master file, created by
   sphinx-quickstart on Fri Mar  4 16:51:06 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Zeep: Python SOAP client 
========================

A fast and hip Python SOAP client ;-)


A quick example::

    >>> from zeep import Client
    >>> client = zeep.Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL')
    >>> print client.service.ConvertSpeed(
    ...     100, 'kilometersPerhour', 'milesPerhour')
    62.137


Complex requests
----------------

Most of the times you need to pass nested data to the soap client. These 
Complex types can be created using the `client.get_type()` method::

    >>> from zeep import Client
    >>> client = zeep.Client('http://my-entrprisy-endpoint.com')
    >>> order_type = client.get_type(
    ...     '{http://tests.python-zeep.org}Order')
    >>> order = order_type(
    ...     number='1234', billing_address=billing_address)
    >>> client.service.submit_order(user_id=1, order=order)


Plugins
-------
Not yet supported, coming soon


WSSE
----
Not yet supported, coming soon



Caching
-------
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



Bugs
----

**Yes there will be bugs! :-)**

If you encounter bugs then please `let me know`_ . A copy of the WSDL file if
possible would be most helpful. If you are really cool then please open a PR
with the fix... :P


.. _let me know: https://github.com/mvantellingen/python-zeep/issues


Contributing
------------

Contributions are welcome!
