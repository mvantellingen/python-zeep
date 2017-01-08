======================================
Multipart support for SOAP Attachments
======================================

If the server responds with a Content-type: multipart, the code will process
the parts individually and return a list of objects. Typically this will be
a ``BodyPart`` object from request_toolbelt.

The ``BodyPart`` object is a ``Response``-like object to an individual
subpart of a multipart response.

Example based on https://www.w3.org/TR/SOAP-attachments

.. code-block:: python

    from zeep import Client

    client = Client('http://www.risky-stuff.com/claim.svc?wsdl')

    parts = client.service.GetClaimDetails('061400a')

    ClaimDetails = parts[0]
    SignedFormTiffImage = parts[1].content
    CrashPhotoJpeg = parts[2].content

