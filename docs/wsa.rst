===================
WS-Addressing (WSA)
===================

.. versionadded:: 0.15

Zeep offers (experimental) support for the `ws-addressing specification`_. The
specification defines a number of soap:Header elements which basically allows
advanced routing of the SOAP messages.

If the WSDL documnt defines that WSA is required then Zeep will automatically
add the required headers to the SOAP envelope. In case you want to customize
this then you can add the ``WsAddressPlugin()`` to the ``Client.plugins`` list.

For example:

.. code-block:: python
    
    from zeep import Client
    from zeep.wsa import WsAddressingPlugin

    client = Client(
        'http://examples.python-zeep.org/basic.wsdl',
        plugins=[WsAddressingPlugin()])
    client.service.DoSomething()


.. note::
    
    The support for ws-addressing is experimental. If you encounter any issues
    then please don't hesistate to create an issue on the github repository.


.. _ws-addressing specification: https://www.w3.org/TR/2006/REC-ws-addr-soap-20060509/
