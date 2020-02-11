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

Example usage::

    >>> from zeep import Client
    >>> from zeep.wsse.signature import Signature
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL', 
    ...     wsse=Signature(
    ...         private_key_filename, public_key_filename, 
    ...         optional_password))


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
