from __future__ import print_function

from requests import Session
from requests.auth import HTTPBasicAuth

import zeep
from zeep.transports import Transport

# Example using basic authentication with a webservice

session = Session()
session.auth = HTTPBasicAuth('username', 'password')
transport_with_basic_auth = Transport(session=session)

client = zeep.Client(
    wsdl='http://nonexistent?WSDL',
    transport=transport_with_basic_auth
)

client.wsdl.dump()
