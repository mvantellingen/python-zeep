==========
Using Zeep
==========

WSDL documents provide a number of operations (functions) per binding. A 
binding is collection of operations which are called via a specific protocol.

These protocols are generally Soap 1.1 or Soap 1.2. As mentioned before, Zeep
also offers experimental support for the Http Get and Http Post bindings. Most
of the time this is an implementation detail, Zeep should offer the same API
to the user independent of the underlying protocol.

One of the first things you will do if you start developing an interface to a
wsdl web service is to get an overview of all available operations and their
call signatures. Zeep offers a command line interface to make this easy.


.. code-block:: bash

    python -mzeep http://www.soapclient.com/xml/soapresponder.wsdl

See ``python -mzeep --help`` for more information.
