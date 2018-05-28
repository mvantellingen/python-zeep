============
SOAP headers
============
SOAP headers are generally used for things like authentication. The header
elements can be passed to all operations using the ``_soapheaders`` kwarg.

There are multiple ways to pass a value to the soapheader.

1. When the SOAP header expects a complex type you can either pass a dict or
   an object created via the ``client.get_element()`` method.
2. When the header expects a simple type value you can pass it directly to the
   ``_soapheaders`` kwarg. (e.g.: ``client.service.Method(_soapheaders=1234)``)
3. Creating custom xsd element objects. For example::

    from zeep import xsd

    header = xsd.Element(
        '{http://test.python-zeep.org}auth',
        xsd.ComplexType([
            xsd.Element(
                '{http://test.python-zeep.org}username', 
                xsd.String()),
        ])
    )
    header_value = header(username='mvantellingen')
    client.service.Method(_soapheaders=[header_value])

4. Another option is to pass an lxml Element object. This is generally useful
   if the wsdl doesn't define a soap header but the server does expect it. 
