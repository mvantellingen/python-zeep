from __future__ import absolute_import, print_function

import logging
import logging.config
import time
import sys

logger = logging.getLogger('zeep')

if __name__ == '__main__':
    use_persistent_cache = '--cache' in sys.argv
    if '--verbose' in sys.argv:
        logging.config.dictConfig({
            'version': 1,
            'formatters': {
                'verbose': {
                    'format': '%(name)s: %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    'formatter': 'verbose',
                },
            },
            'loggers': {
                'zeep': {
                    'level': 'DEBUG',
                    'propagate': True,
                    'handlers': ['console'],
                },
                'zeep.xsd': {
                    'level': 'INFO',
                    'propagate': True,
                    'handlers': ['console'],
                },
            }
        })

    from zeep.client import Client
    from zeep.cache import SqliteCache

    if len(sys.argv) < 2:
        print("Missing argument. Please pass a WSDL", file=sys.stderr)
        sys.exit(1)

    cache = SqliteCache(persistent=use_persistent_cache)
    st = time.time()
    client = Client(sys.argv[1], cache=cache)
    logger.debug("Loading WSDL took %sms", (time.time() - st) * 1000)
    sys.exit(0)
