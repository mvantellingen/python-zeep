import os

import zeep


def test_hello_world():
    path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "hello_world_recursive.wsdl"
    )
    client = zeep.Client(path)
    client.wsdl.dump()
