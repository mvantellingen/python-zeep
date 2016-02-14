

Usage::

    from zeep import Client

    client = Client(
        wsdl='tests/wsdl_files/example.rst'
    )

    client.service.ping()
