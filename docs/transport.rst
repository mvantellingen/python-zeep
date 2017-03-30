Transports
==========
If you need to change options like cache, timeout or ssl verification you will
need to create an instance of the Transport class yourself.

For instance to disable SSL verification you will need to create a new
:class:`requests.Session` instance and set the ``verify`` attribute to
``False``.

.. code-block:: python

    from requests import Session
    from zeep import Client
    from zeep.transports import Transport

    session = Session()
    session.verify = False
    transport = Transport(session=session)
    client = Client(
        'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
        transport=transport)


To set a transport timeout use the `timeout` option. The default timeout is 300
seconds:

.. code-block:: python

    from zeep import Client
    from zeep.transports import Transport

    transport = Transport(timeout=10)
    client = Client(
        'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
        transport=transport)


Caching
-------
By default zeep doesn't use a caching backend.  For performance benefits it is
advised to use the SqliteCache backend.  It caches the WSDL and XSD files for
1 hour by default. To use the cache backend init the client with:

.. code-block:: python

    from zeep import Client
    from zeep.cache import SqliteCache
    from zeep.transports import Transport

    transport = Transport(cache=SqliteCache())
    client = Client(
        'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
        transport=transport)


Changing the SqliteCache settings can be done via:

.. code-block:: python

    from zeep import Client
    from zeep.cache import SqliteCache
    from zeep.transports import Transport
    cache = SqliteCache(path='/tmp/sqlite.db', timeout=60)
    transport = Transport(cache=cache)
    client = Client(
        'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
        transport=transport)


Another option is to use the InMemoryCache backend.  It internally uses a
global dict to store urls with the corresponding content.


HTTP Authentication
-------------------
While some providers incorporate security features in the header of a SOAP message,
others use the HTTP Authentication header.  In the latter case,
you can just create a :class:`requests.Session` object with the auth set and pass it
to the Transport class.

.. code-block:: python

    from requests import Session
    from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
    from zeep import Client
    from zeep.transports import Transport

    session = Session()
    session.auth = HTTPBasicAuth(user, password)
    client = Client('http://my-endpoint.com/production.svc?wsdl',
        transport=Transport(session=session))


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
