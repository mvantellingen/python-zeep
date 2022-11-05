========================
Zeep: Python SOAP client
========================

A Python SOAP client

Highlights:
 * Compatible with Python 3.7, 3.8, 3.9, 3.10, 3.11 and PyPy3
 * Build on top of lxml, requests and httpx
 * Support for Soap 1.1, Soap 1.2 and HTTP bindings
 * Support for WS-Addressing headers
 * Support for WSSE (UserNameToken / x.509 signing)
 * Support for asyncio using the httpx module
 * Experimental support for XOP messages


Please see for more information the documentation at
http://docs.python-zeep.org/


.. start-no-pypi

Status
------


**I consider this library to be stable. Since no new developments happen around the SOAP specification it won't be updated that much. Good PR's which fix bugs are always welcome however.**


.. image:: https://readthedocs.org/projects/python-zeep/badge/?version=latest
    :target: https://readthedocs.org/projects/python-zeep/

.. image:: https://github.com/mvantellingen/python-zeep/workflows/Python%20Tests/badge.svg
    :target: https://github.com/mvantellingen/python-zeep/actions?query=workflow%3A%22Python+Tests%22

.. image:: http://codecov.io/github/mvantellingen/python-zeep/coverage.svg?branch=master
    :target: http://codecov.io/github/mvantellingen/python-zeep?branch=master

.. image:: https://img.shields.io/pypi/v/zeep.svg
    :target: https://pypi.python.org/pypi/zeep/

.. end-no-pypi

Installation
------------

.. code-block:: bash

    pip install zeep

Note that the latest version to support Python 2.7, 3.3, 3.4 and 3.5 is Zeep
3.4, install via `pip install zeep==3.4.0`

Zeep uses the lxml library for parsing xml. See
https://lxml.de/installation.html for the installation requirements.

Usage
-----
.. code-block:: python

    from zeep import Client

    client = Client('tests/wsdl_files/example.rst')
    client.service.ping()


To quickly inspect a WSDL file use::

    python -m zeep <url-to-wsdl>


Please see the documentation at http://docs.python-zeep.org for more
information.


Support
=======

If you want to report a bug then please first read
http://docs.python-zeep.org/en/master/reporting_bugs.html

Please only report bugs and not support requests to the GitHub issue tracker.
