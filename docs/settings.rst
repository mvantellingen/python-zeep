.. _settings:

========
Settings
========

.. currentmodule:: zeep.settings

.. versionadded:: 3.0

Context manager
---------------
You can set various options directly as attribute on the client or via a
context manager.

For example to let zeep return the raw response directly instead of processing
it you can do the following:

.. code-block:: python

    from zeep import Client
    from zeep import xsd

    client = Client('http://my-endpoint.com/production.svc?wsdl')

    with client.settings(raw_response=True):
        response = client.service.myoperation()

        # response is now a regular requests.Response object
        assert response.status_code == 200
        assert response.content

API
---

.. automodule:: zeep.settings
   :members:
