========================
Zeep: Python SOAP client 
========================

A fast and modern Python SOAP client

| Website: http://docs.python-zeep.org/
| IRC: #python-zeep on Freenode

Highlights:
 * Modern codebase compatible with Python 2.7, 3.3, 3.4, 3.5 and PyPy
 * Build on top of lxml and requests
 * Supports recursive WSDL and XSD documents.
 * Supports the xsd:choice and xsd:any elements.
 * Uses the defusedxml module for handling potential XML security issues
 * Support for WSSE (UsernameToken only for now)
 * Experimental support for HTTP bindings
 * Experimental support for WS-Addressing headers
 * Experimental support for asyncio via aiohttp (Python 3.5+)

Features still in development include:
 * WSSE x.509 support (BinarySecurityToken)
 * WS Policy support

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

.. image:: https://requires.io/github/mvantellingen/python-zeep/requirements.svg?branch=master
     :target: https://requires.io/github/mvantellingen/python-zeep/requirements/?branch=master

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

    python -mzeep <url-to-wsdl>


Please see the documentation at http://docs.python-zeep.org for more
information.


Support
=======

If you encounter bugs then please `let me know`_ .  A copy of the WSDL file if
possible would be most helpful. 

I'm also able to offer commercial support.  As in contracting work. Please
contact me at info@mvantellingen.nl for more information. If you just have a
random question and don't intent to actually pay me for my support then please
DO NOT email me at that e-mail address but just use stackoverflow or something..

.. _let me know: https://github.com/mvantellingen/python-zeep/issues
