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


To set a transport timeout use the `timeout` option. The default timeout is 300 seconds::

    >>> from zeep import Client
    >>> from zeep.transports import Transport
    >>> transport = Transport(timeout=10)
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
    ...     transport=transport)


Caching
-------
The default cache backend is SqliteCache.  It caches the WSDL and XSD files for 
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



HTTP Authentication
-------------------
While some providers incorporate security features in the header of a SOAP message,
others use the HTTP Authentication header.  In the latter case,
you can use any method supported by ``requests``.

.. code-block:: python

    from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
    from zeep import Client
    from zeep.transports import Transport

    client = Client('http://my-endpoint.com/production.svc?wsdl',
        transport=Transport(http_auth=HTTPBasicAuth(user, password)))


.. _debugging:

Debugging
---------
To see the SOAP XML messages which are sent to the remote server and the 
response received you can set the Python logger level to DEBUG for the
``zeep.transports`` module. Since 0.15 this can also be achieved via the
:ref:`plugin-history`.

.. code-block:: python

    import logging.config

    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'verbose': {
                'format': '%(name)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'zeep.transports': {
                'level': 'DEBUG',
                'propagate': True,
                'handlers': ['console'],
            },
        }
    })
