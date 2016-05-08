from __future__ import absolute_import, print_function

import argparse
import logging
import logging.config
import time

from zeep.cache import SqliteCache
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
            }
        })

    if args.profile:
        import cProfile
        profile = cProfile.Profile()
        profile.enable()

    cache = SqliteCache(persistent=args.cache)
    transport = Transport(cache=cache)
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
