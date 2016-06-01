WS-Security (WSSE)
==================

WS-Security incorporates security features in the header of a SOAP message.

UsernameToken
-------------
Only the UsernameToken profile is supported for now.  It supports both the 
passwordText and passwordDigest methods::

    >>> from zeep import Client
    >>> from zeep.wsse.username import UsernameToken
    >>> client = Client(
    ...     'http://www.webservicex.net/ConvertSpeed.asmx?WSDL', 
    ...     wsse=UsernameToken('username', 'password'))

To use the passwordDigest method you need to supply `use_digest=True` to the
`UsernameToken` class.


