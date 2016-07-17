from __future__ import print_function
import zeep
from zeep.transports import Transport

# Example using basic authentication with a webservice

transport_with_basic_auth = Transport(http_auth=('username', 'password'))

client = zeep.Client(
    wsdl='http://nonexistent?WSDL',
    transport=transport_with_basic_auth
)

client.wsdl.dump()
