ZEEP
====

**!!In development!!**

SOAP client for Python using the lxml and requests packages

Status
------
.. image:: https://travis-ci.org/mvantellingen/python-zeep.svg?branch=master
    :target: https://travis-ci.org/mvantellingen/python-zeep

.. image:: http://codecov.io/github/mvantellingen/python-zeep/coverage.svg?branch=master 
    :target: http://codecov.io/github/mvantellingen/python-zeep?branch=master


Usage
-----
.. code-block:: python

    from zeep import Client

    client = Client(
        wsdl='tests/wsdl_files/example.rst'
    )

    client.service.ping()
