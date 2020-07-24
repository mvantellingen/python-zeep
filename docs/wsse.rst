WS-Security (WSSE)
==================

WS-Security incorporates security features in the header of a SOAP message.

UsernameToken
-------------
The UsernameToken supports both the passwordText and passwordDigest methods::

    >>> from zeep import Client
    >>> from zeep.wsse.username import UsernameToken
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL', 
    ...     wsse=UsernameToken('username', 'password'))

To use the passwordDigest method you need to supply `use_digest=True` to the
`UsernameToken` class.


Signature (x509)
----------------

To use the wsse.Signature() plugin you will need to install the `xmlsec`_
module. See the `README`_ for xmlsec for the required dependencies on your 
platform.

To append the security token as `BinarySecurityToken`, you can use wsse.BinarySignature() plugin.

Example usage A::

    >>> from zeep import Client
    >>> from zeep.wsse.signature import Signature
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL', 
    ...     wsse=Signature(
    ...         private_key_filename, public_key_filename, 
    ...         optional_password))


To skip response signature verification set `verify_reply_signature=False`

To configure different certificate for response verify proces set `response_key_file` or
and `response_certfile`.

.. _xmlsec: https://pypi.python.org/pypi/xmlsec
.. _README: https://github.com/mehcode/python-xmlsec


UsernameToken and Signature together
------------------------------------

To use UsernameToken and Signature together, then you can pass both together
to the client in a list

    >>> from zeep import Client
    >>> from zeep.wsse.username import UsernameToken
    >>> from zeep.wsse.signature import Signature
    >>> user_name_token = UsernameToken('username', 'password')
    >>> signature = Signature(private_key_filename, public_key_filename,
    ...     optional_password)
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL',
    ...     wsse=[user_name_token, signature])


UsernameToken with Timestamp token
------------------------------------

To use UsernameToken with Timestamp token, first you need an instance of `WSU.Timestamp()`, then extend it with a list
containing `WSU.Created()` and `WSU.Expired()` elements, finally pass it as `timestamp_token` keyword argument
to `UsernameToken()`.

    >>> import datetime
    >>> from zeep import Client
    >>> from zeep.wsse.username import UsernameToken
    >>> from zeep.wsse.utils import WSU
    >>> timestamp_token = WSU.Timestamp()
    >>> today_datetime = datetime.datetime.today()
    >>> expires_datetime = today_datetime + datetime.timedelta(minutes=10)
    >>> timestamp_elements = [
    ...         WSU.Created(today_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")),
    ...         WSU.Expires(expires_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"))
    ...]
    >>> timestamp_token.extend(timestamp_elements)
    >>> user_name_token = UsernameToken('username', 'password', timestamp_token=timestamp_token)
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL', wsse=user_name_token
    ...)
