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

.. image:: https://img.shields.io/pypi/v/zeep.svg
    :target: https://pypi.python.org/pypi/zeep/

.. image:: https://requires.io/github/mvantellingen/python-zeep/requirements.svg?branch=master
     :target: https://requires.io/github/mvantellingen/python-zeep/requirements/?branch=master


Usage
-----
.. code-block:: python

    from zeep import Client

    client = Client(wsdl='tests/wsdl_files/example.rst')
    client.service.ping()


To quickly inspect a WSDL file use::

    python -mzeep <url-to-wsdl>


Bugs
----

**Yes there will be bugs! :-)**

If you encounter bugs then please `let me know`_ . A copy of the WSDL file if
possible would be most helpful. If you are really cool then please open a PR
with the fix... :P


.. _let me know: https://github.com/mvantellingen/python-zeep/issues
