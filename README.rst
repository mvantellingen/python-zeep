========================
Zeep: Python SOAP client 
========================

A fast and modern Python SOAP client

Highlights:
 * Compatible with Python 2.7, 3.3, 3.4, 3.5, 3.6, 3.7 and PyPy
 * Build on top of lxml and requests
 * Support for Soap 1.1, Soap 1.2 and HTTP bindings
 * Support for WS-Addressing headers
 * Support for WSSE (UserNameToken / x.509 signing)
 * Support for tornado async transport via gen.coroutine (Python 2.7+)
 * Support for asyncio via aiohttp (Python 3.5+)
 * Experimental support for XOP messages


Please see for more information the documentation at
http://docs.python-zeep.org/


.. start-no-pypi

Status
------

.. image:: https://readthedocs.org/projects/python-zeep/badge/?version=latest
    :target: https://readthedocs.org/projects/python-zeep/
   
.. image:: https://travis-ci.org/mvantellingen/python-zeep.svg?branch=master
    :target: https://travis-ci.org/mvantellingen/python-zeep

.. image:: https://ci.appveyor.com/api/projects/status/im609ng9h29vt89r?svg=true
    :target: https://ci.appveyor.com/project/mvantellingen/python-zeep

.. image:: http://codecov.io/github/mvantellingen/python-zeep/coverage.svg?branch=master 
    :target: http://codecov.io/github/mvantellingen/python-zeep?branch=master

.. image:: https://img.shields.io/pypi/v/zeep.svg
    :target: https://pypi.python.org/pypi/zeep/

.. end-no-pypi

Installation
------------

.. code-block:: bash

    pip install zeep


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
