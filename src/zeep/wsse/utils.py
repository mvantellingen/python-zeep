import datetime

import pytz
from lxml.builder import ElementMaker

from zeep.wsdl.utils import get_or_create_header

NSMAP = {
    'wsse': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd',
}
WSSE = ElementMaker(namespace=NSMAP['wsse'])


def get_security_header(doc):
    """Return the security header. If the header doesn't exist it will be
    created.

    """
    header = get_or_create_header(doc)
    security = header.find('wsse:Security', namespaces=NSMAP)
    if security is None:
        security = WSSE.Security()
        header.append(security)
    return security


def get_timestamp(timestamp=None):
    timestamp = timestamp or datetime.datetime.utcnow()
    timestamp = timestamp.replace(tzinfo=pytz.utc, microsecond=0)
    return timestamp.isoformat()
