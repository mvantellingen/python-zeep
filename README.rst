ZEEP
====

SOAP client for Python using the lxml and requests packages. This package is
still in development. Current releases should be considered proof of concepts.

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

    client = Client(wsdl='tests/wsdl_files/example.rst')
    client.service.ping()


Bugs
----

If you encounter bugs then please `let me know`_. A copy of the WSDL file if
possible would be most helpful.

.. _report a bug: https://github.com/mvantellingen/python-zeep/issues
