from __future__ import absolute_import, print_function

import sys

if __name__ == '__main__':
    use_persistent_cache = '--cache' in sys.argv

    from zeep.client import Client
    from zeep.cache import SqliteCache

    if len(sys.argv) < 2:
        print("Missing argument. Please pass a WSDL", file=sys.stderr)
        sys.exit(1)

    cache = SqliteCache(persistent=use_persistent_cache)
    client = Client(sys.argv[1], cache=cache)
    client.wsdl.dump()
    sys.exit(0)
