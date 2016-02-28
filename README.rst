ZEEP
====

**!!In development!!**

SOAP client for Python using the lxml and requests packages

Usage
-----
.. code-block:: python

    from zeep import Client

    client = Client(
        wsdl='tests/wsdl_files/example.rst'
    )

    client.service.ping()
