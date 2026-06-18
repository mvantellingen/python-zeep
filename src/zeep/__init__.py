from importlib.metadata import PackageNotFoundError, version

from zeep.client import AsyncClient, CachingClient, Client
from zeep.plugins import Plugin
from zeep.settings import Settings
from zeep.transports import Transport
from zeep.xsd.valueobjects import AnyObject

try:
    __version__ = version("zeep")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
__all__ = [
    "AsyncClient",
    "CachingClient",
    "Client",
    "Plugin",
    "Settings",
    "Transport",
    "AnyObject",
]
