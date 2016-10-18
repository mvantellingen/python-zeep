from __future__ import absolute_import, print_function

import argparse
import logging
import logging.config
import time

from six.moves.urllib.parse import urlparse
from zeep.cache import InMemoryCache, SqliteCache
from zeep.client import Client
from zeep.transports import Transport

logger = logging.getLogger('zeep')


def parse_arguments(args=None):
    parser = argparse.ArgumentParser(description='Zeep: The SOAP client')
    parser.add_argument(
        'wsdl_file', type=str, help='Path or URL to the WSDL file',
        default=None)
    parser.add_argument(
        '--cache', action='store_true', help='Enable cache')
    parser.add_argument(
        '--no-verify', action='store_true', help='Disable SSL verification')
    parser.add_argument(
        '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument(
        '--profile', help="Enable profiling and save output to given file")
    return parser.parse_args(args)


def main(args):
    if args.verbose:
        logging.config.dictConfig({
            'version': 1,
            'formatters': {
                'verbose': {
                    'format': '%(name)20s: %(message)s'
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
            }
        })

    if args.profile:
        import cProfile
        profile = cProfile.Profile()
        profile.enable()

    cache = SqliteCache() if args.cache else InMemoryCache()
    transport_kwargs = {'cache': cache}

    if args.no_verify:
        transport_kwargs['verify'] = False

    result = urlparse(args.wsdl_file)
    if result.username or result.password:
        transport_kwargs['http_auth'] = (result.username, result.password)

    transport = Transport(**transport_kwargs)
    st = time.time()
    client = Client(args.wsdl_file, transport=transport)
    logger.debug("Loading WSDL took %sms", (time.time() - st) * 1000)

    if args.profile:
        profile.disable()
        profile.dump_stats(args.profile)
    client.wsdl.dump()


if __name__ == '__main__':
    args = parse_arguments()
    main(args)
