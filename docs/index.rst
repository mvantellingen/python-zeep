========================
Zeep: Python SOAP client 
========================

A fast and modern Python SOAP client

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


A simple example:

.. code-block:: python

    from zeep import Client

    client = Client('http://www.webservicex.net/ConvertSpeed.asmx?WSDL')
    result = client.service.ConvertSpeed(
        100, 'kilometersPerhour', 'milesPerhour')

    assert result == 62.137


Quick Introduction
==================

Zeep inspects the wsdl document and generates the corresponding bindings.  This
provides an easy to use programmatic interface to a soap server.

The emphasis is on Soap 1.1 and Soap 1.2, however Zeep also offers experimental
support for HTTP Get and Post bindings.

Parsing the XML documents is done by using the lxml library. This is the most
performant and compliant Python XML library currently available. This results
in major speed benefits when retrieving large soap responses.

The SOAP specifications are unfortunately really vague and leave a lot of
things open for interpretation.  Due to this there are a lot of WSDL documents
available which are invalid or SOAP servers which contain bugs. Zeep tries to
be as compatible as possible but there might be cases where you run into 
problems. Don't hesitate to submit an issue in this case (please see 
:ref:`reporting_bugs`).


Getting started
===============

You can install the latest version of zeep using pip::

    pip install zeep

The first thing you generally want to do is inspect the wsdl file you need to
implement. This can be done with::

    python -mzeep <wsdl>


See ``python -mzeep --help`` for more information about this command.


.. note:: Since this module hasn't reached 1.0.0 yet their might be minor
          releases which introduce backwards compatible changes. While I try 
          to keep this to a minimum it can still happen. So as always pin the 
          version of zeep you used (e.g. ``zeep==0.14.0``').



A simple use-case
-----------------

To give you an idea how zeep works a basic example.

.. code-block:: python

    import zeep

    wsdl = 'http://www.soapclient.com/xml/soapresponder.wsdl'
    client = zeep.Client(wsdl=wsdl)
    print(client.service.Method1('Zeep', 'is cool'))

The WSDL used above only defines one simple function (``Method1``) which is 
made available by zeep via ``client.service.Method1``. It takes two arguments
and returns a string. To get an overview of the services available on the 
endpoint you can run the following command in your terminal.

.. code-block:: bash

    python -mzeep http://www.soapclient.com/xml/soapresponder.wsdl


More information
================

.. toctree::
   :maxdepth: 2
   :name: mastertoc

   in_depth
   datastructures
   transport
   wsa
   wsse
   plugins
   helpers
   reporting_bugs
   changes


Support
=======

If you encounter bugs then please `let me know`_ . Please see :doc:`reporting_bugs`
for information how to best report them.

I'm also able to offer commercial support.  Please contact me at
info@mvantellingen.nl for more information.


.. _let me know: https://github.com/mvantellingen/python-zeep/issues
