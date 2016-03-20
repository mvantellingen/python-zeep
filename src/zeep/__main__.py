from __future__ import absolute_import, print_function

import sys

if __name__ == '__main__':
    from zeep.client import Client

    if len(sys.argv) < 2:
        print("Missing argument. Please pass a WSDL", file=sys.stderr)
        sys.exit(1)

    client = Client(sys.argv[1])
    client.wsdl.dump()
    sys.exit(0)
