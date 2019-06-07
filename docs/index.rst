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


A simple example:

.. code-block:: python

    from zeep import Client

    client = Client('http://www.webservicex.net/ConvertSpeed.asmx?WSDL')
    result = client.service.ConvertSpeed(
        100, 'kilometersPerhour', 'milesPerhour')

    assert result == 62.137


Quick Introduction
==================

Zeep inspects the WSDL document and generates the corresponding code to use the
services and types in the document.  This provides an easy to use programmatic
interface to a SOAP server.

The emphasis is on SOAP 1.1 and SOAP 1.2, however Zeep also offers support for
HTTP Get and Post bindings.

Parsing the XML documents is done by using the `lxml`_ library. This is the most
performant and compliant Python XML library currently available. This results
in major speed benefits when processing large SOAP responses.

The SOAP specifications are unfortunately really vague and leave a lot of
things open for interpretation.  Due to this there are a lot of WSDL documents
available which are invalid or SOAP servers which contain bugs. Zeep tries to
be as compatible as possible but there might be cases where you run into
problems. Don't hesitate to submit an issue in this case (but please first
read :ref:`reporting_bugs`).

.. _lxml: http://lxml.de


Installation
============

Zeep is a pure-python module.  This means that there is no C code which needs
to be compiled.  However the lxml dependency does contain C code since it uses
libxml2 and libxslt.  For linux/bsd this means you need to install libxml2-dev
and libxslt-dev packages.  For Windows this is unfortunately a bit more
complicated.  The easiest way is to install lxml via wheel files since that
contains already compiled code for your platform.

To install wheel files you need a recent pip client.  See
https://pip.pypa.io/en/stable/installing/ how to install pip on your platform.


If you have installed pip then run::

    pip install zeep


This assumes that there are wheel files available for the latest lxml release.
If that is not the case (https://pypi.python.org/pypi/lxml/) then first
install lxml 4.2.5 since that release should have the wheel files for all
platforms::

    pip install lxml==4.2.5 zeep


When you want to use wsse.Signature() you will need to install the python
xmlsec module. This can be done by installing the ``xmlsec`` extras::

    pip install zeep[xmlsec]

For the asyncio support in Python 3.5+ the aiohttp module is required, this
can be installed with the ``async`` extras::

    pip install zeep[async]


For the tornado support in Python 2.7+ the tornado module is required, this
can be installed with the ``tornado`` extras::

    pip install zeep[tornado]


Getting started
===============

The first thing you generally want to do is inspect the wsdl file you need to
implement. This can be done with::

    python -mzeep <wsdl>


See ``python -mzeep --help`` for more information about this command.


.. note:: Zeep follows `semver`_ for versioning, however bugs can always occur.
          So as always pin the version of zeep you tested with
          (e.g. ``zeep==3.4.0``').


.. _semver: http://semver.org/


A simple use-case
=================

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


.. note::

    Note that unlike suds, zeep doesn't enable caching of the wsdl documents
    by default. This means that everytime you initialize the client requests
    are done to retrieve the wsdl contents.


User guide
==========

.. toctree::
   :maxdepth: 2

   in_depth
   client
   settings
   transport
   headers
   datastructures
   attachments
   wsa
   wsse
   plugins
   helpers
   reporting_bugs


API Documentation
=================
.. toctree::
   :maxdepth: 2

   api
   internals


Changelog
=========
.. toctree::
   :maxdepth: 2

   changes
