========================
Zeep: Python SOAP client 
========================

A fast and hip Python SOAP client ;-)

Highlights:
 * Modern codebase compatible with Python 2.7, 3.3, 3.4, 3.5 and PyPy
 * Build on top of lxml and requests
 * Supports recursive WSDL and XSD documents.
 * Supports the xsd:choice and xsd:any elements.
 * Uses the defusedxml module for handling potential XML security issues
 * Support for WSSE (UsernameToken only for now)
 * Experimental support for HTTP bindings

Features still in development include:
 * WSSE x.509 support (BinarySecurityToken)
 * XML validation using lxml XMLSchema's

 Please see for more information the documentation at 
 http://docs.python-zeep.org/



Status
------

.. image:: https://readthedocs.org/projects/python-zeep/badge/?version=latest
    :target: https://readthedocs.org/projects/python-zeep/
   
.. image:: https://travis-ci.org/mvantellingen/python-zeep.svg?branch=master
    :target: https://travis-ci.org/mvantellingen/python-zeep

.. image:: http://codecov.io/github/mvantellingen/python-zeep/coverage.svg?branch=master 
    :target: http://codecov.io/github/mvantellingen/python-zeep?branch=master

.. image:: https://img.shields.io/pypi/v/zeep.svg
    :target: https://pypi.python.org/pypi/zeep/

.. image:: https://requires.io/github/mvantellingen/python-zeep/requirements.svg?branch=master
     :target: https://requires.io/github/mvantellingen/python-zeep/requirements/?branch=master


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

    python -mzeep <url-to-wsdl>


Please see the documentation at http://docs.python-zeep.org for more
information.


Bugs
----

If you encounter bugs then please `let me know`_ . A copy of the WSDL file if
possible would be most helpful. If you are really cool then please open a PR
with the fix... :P


.. _let me know: https://github.com/mvantellingen/python-zeep/issues
