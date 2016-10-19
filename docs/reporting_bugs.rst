.. _reporting_bugs:

Reporting bugs
==============

The SOAP specifications are pretty bad and unclear for a lot of use-cases. This
results in a lot of (older) SOAP servers which don't implement the
specifications correctly (or implement them in a way Zeep doesn't expect).
Of course there is also a good chance that Zeep doesn't implement something
correctly ;-) I'm always interested in the latter.

Since Zeep is a module I've created and currently maintain mostly in my spare
time I need as much information as possible to quickly analyze/fix issues.

There are basically three majors parts where bugs can happen, these are:

1. Parsing the WSDL
2. Creating the XML for the request
3. Parsing the XML from the response


The first one is usually pretty easy to debug if the WSDL is publicly 
accessible. If that isn't the case then you might be able to make it anonymous.


Required information
--------------------
Please provide the following information:

1. The version of zeep (or if you are running master the commit hash/date)
2. The WSDL you are using
3. An example script (please see below)



Errors when creating the request
--------------------------------

Create a new python script using the code below. The first argument to the
create_message method is the name of the operation/method and after that the
args / kwargs you normally pass.

.. code-block:: python

    from lxml import etree
    from zeep import Client

    client = Client('YOUR-WSDL')

    # client.service.OPERATION_NAME(args, kwargs) becomes
    node = client.service._binding.create_message(
        'OPERATION_NAME', args, kwargs)

    print(etree.tostring(node, pretty_print=True))



Errors when parsing the response
--------------------------------

The first step is to retrieve the XML which is returned from the server, You
need to enable debugging for this. Please see :ref:`debugging` for a detailed
description.

The next step is to create a python script which exposes the problem, an 
example is the following.

.. code-block:: python

    import pretend  # pip install pretend

    from zeep import Client
    from zeep.transports import Transport

    # Replace YOUR-WSDL and OPERATION_NAME with the wsdl url 
    # and the method name you are calling. The response
    # needs to be set in the content=""" """ var.

    client = Client('YOUR-WSDL')
    response = pretend.stub(
        status_code=200,
        headers=[],
        content="""
            <!-- The response from the server -->
        """)

    operation = client.service._binding._operations['OPERATION_NAME']
    result = client.service._binding.process_reply(
        client, operation, response)

    print(result)
