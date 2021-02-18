Transports
==========
If you need to change options like cache, timeout or TLS (or SSL) verification
you will need to create an instance of the Transport class yourself.

.. note::
    Secure Sockets Layer (SSL) has been deprecated in favor of Transport
    Layer Security (**TLS**). SSL 2.0 was prohibited in 2011 and SSL 3.0
    in June 2015.

TLS verification
----------------
If you need to verify the TLS connection (in case you have a self-signed
certificate for your host), the best way is to create a
:class:`requests.Session` instance and add the information to that Session,
so it keeps persistent:

.. code-block:: python

    from requests import Session
    from zeep import Client
    from zeep.transports import Transport

    session = Session()
    session.verify = 'path/to/my/certificate.pem'
    transport = Transport(session=session)
    client = Client(
        'http://my.own.sslhost.local/service?WSDL',
        transport=transport)


.. hint::
    Make sure that the certificate you refer to is a CA_BUNDLE, meaning it
    contains a root CA and an intermediate CA. Accepted are only X.509 ASCII
    files (file extension ``.pem``, sometimes ``.crt``). If you have two
    different files, you must combine them manually into one.

Alternatively, instead of using ``session.verify`` you can use
``session.cert`` if you just want to use an TLS client certificate.

To **disable TLS verification** (not recommended!) you will need to set
``verify`` to ``False``.

.. code-block:: python

    session = Session()
    session.verify = False

Or even simpler way:

.. code-block:: python

    client.transport.session.verify = False

Remember: this should be only done for testing purposes. Python's ``urllib3``
will warn you with a ``InsecureRequestWarning``.

See :class:`requests.Session` for further details.

Session timeout
---------------

To set a transport timeout use the `timeout` option. The default timeout is 300
seconds:

.. code-block:: python

    from zeep import Client
    from zeep.transports import Transport

    transport = Transport(timeout=10)
    client = Client(
        'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
        transport=transport)


Using HTTP or SOCKS Proxy
-------------------------

By default, zeep uses ``requests`` as transport layer, which allows to
define proxies using the ``proxies`` attribute of :class:`requests.Session`:

.. code-block:: python

    from zeep import Client

    client = Client(
        'http://my.own.sslhost.local/service?WSDL')

    client.transport.session.proxies = {
        # Utilize for all http/https connections
        'http': 'foo.bar:3128',
        'https': 'foo.bar:3128',
        # Utilize for certain URL
        'http://specific.host.example': 'foo.bar:8080',
        # Or use socks5 proxy (requires requests[socks])
        'https://socks5-required.example': 'socks5://foo.bar:8888',
    }

In order to use **SOCKS** proxies, requests needs to be installed with
additional packages (for example ``pip install -U requests[socks]``).

.. _transport_caching:

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
