===============
Writing plugins
===============

You can write plugins for zeep which can be used to process/modify data before
it is send to the server (egress) and after it is received (ingress).

Writing a plugin is really simple and best explained via an example.


.. code-block:: python

    from lxml import etree
    from zeep import Plugin

    class MyLoggingPlugin(Plugin):

        def ingress(self, envelope, http_headers):
            print(etree.tostring(envelope, pretty_print=True))
            return envelope, http_headers

        def egress(self, envelope, http_headers):
            print(etree.tostring(envelope, pretty_print=True))
            return envelope, http_headers


The plugin can implement two methods: ``ingress`` and ``egress``. Both methods
should always return an envelop (lxml element) and the http headers.

To register this plugin you need to pass it to the client. Plugins are always
executed sequentially.

.. code-block:: python

    from zeep import Client

    client = Client(..., plugins=[MyLoggingPlugin()])
