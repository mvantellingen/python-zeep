import importlib.resources
import os.path
import typing
from urllib.parse import urljoin, urlparse, urlunparse

from lxml import etree
from lxml.etree import Resolver, XMLParser, fromstring

from zeep.exceptions import (
    DTDForbidden,
    EntitiesForbidden,
    ExternalReferenceForbidden,
    XMLSyntaxError,
)
from zeep.settings import Settings

# Well known schemas which are shipped with zeep, so loading them doesn't
# depend on the availability of the remote server (see #1417). The SOAP
# encoding schema is also auto imported by zeep when a WSDL references it
# without importing it, see ``zeep.xsd.const.AUTO_IMPORT_NAMESPACES``.
BUNDLED_SCHEMAS = {
    "http://schemas.xmlsoap.org/soap/encoding/": "soap-encoding.xsd",
    "https://schemas.xmlsoap.org/soap/encoding/": "soap-encoding.xsd",
}


def load_bundled_schema(url) -> typing.Optional[bytes]:
    """Return the content of the schema shipped with zeep for the given url,
    or None if zeep doesn't ship one or the file is missing.

    """
    filename = BUNDLED_SCHEMAS.get(str(url))
    if filename is None:
        return None
    try:
        return (
            importlib.resources.files("zeep")
            .joinpath("schemas")
            .joinpath(filename)
            .read_bytes()
        )
    except OSError:
        # The file is missing when zeep is packaged without its package data
        # (for example by PyInstaller), load it through the transport instead.
        return None


class ImportResolver(Resolver):
    """Custom lxml resolve to use the transport object"""

    def __init__(self, transport, settings=None):
        self.transport = transport
        self.settings = settings or Settings()

    def resolve(self, url, pubid, context):
        if urlparse(url).scheme in ("http", "https"):
            if self.settings.forbid_external:
                raise ExternalReferenceForbidden(url)
            content = self.transport.load(url)
            return self.resolve_string(content, context)


def parse_xml(content: str, transport, base_url=None, settings=None):
    """Parse an XML string and return the root Element.

    :param content: The XML string
    :type content: str
    :param transport: The transport instance to load imported documents
    :type transport: zeep.transports.Transport
    :param base_url: The base url of the document, used to make relative
      lookups absolute.
    :type base_url: str
    :param settings: A zeep.settings.Settings object containing parse settings.
    :type settings: zeep.settings.Settings
    :returns: The document root
    :rtype: lxml.etree._Element

    """
    settings = settings or Settings()
    recover = not settings.strict
    parser = XMLParser(
        remove_comments=True,
        resolve_entities=False,
        recover=recover,
        huge_tree=settings.xml_huge_tree,
    )
    parser.resolvers.add(ImportResolver(transport, settings))
    try:
        elementtree = fromstring(content, parser=parser, base_url=base_url)
        docinfo = elementtree.getroottree().docinfo
        if docinfo.doctype:
            if settings.forbid_dtd:
                raise DTDForbidden(
                    docinfo.doctype, docinfo.system_url, docinfo.public_id
                )
        if settings.forbid_entities:
            for dtd in docinfo.internalDTD, docinfo.externalDTD:
                if dtd is None:
                    continue
                for entity in dtd.iterentities():
                    raise EntitiesForbidden(entity.name, entity.content)

        return elementtree
    except etree.XMLSyntaxError as exc:
        raise XMLSyntaxError(
            "Invalid XML content received (%s)" % exc.msg, content=content
        )


def load_external(
    url: typing.Union[typing.IO, str],
    transport,
    base_url=None,
    settings=None,
    *,
    _initial: bool = False,
):
    """Load an external XML document.

    :param url:
    :param transport:
    :param base_url:
    :param settings: A zeep.settings.Settings object containing parse settings.
    :type settings: zeep.settings.Settings
    :param _initial: Internal flag set by zeep when loading the user-supplied
      entry-point document; transitive imports leave it False so that
      ``settings.forbid_external`` can block them.

    """
    settings = settings or Settings()
    if hasattr(url, "read"):
        content = url.read()
    else:
        if base_url:
            url = absolute_location(url, base_url)
        bundled = load_bundled_schema(url)
        if bundled is not None:
            return parse_xml(bundled, transport, base_url, settings=settings)
        if not _initial and settings.forbid_external:
            if urlparse(str(url)).scheme in ("http", "https"):
                raise ExternalReferenceForbidden(url)
        content = transport.load(url)
    return parse_xml(content, transport, base_url, settings=settings)


async def load_external_async(
    url: typing.IO,
    transport,
    base_url=None,
    settings=None,
    *,
    _initial: bool = False,
):
    """Load an external XML document.

    :param url:
    :param transport:
    :param base_url:
    :param settings: A zeep.settings.Settings object containing parse settings.
    :type settings: zeep.settings.Settings
    :param _initial: Internal flag set by zeep when loading the user-supplied
      entry-point document; transitive imports leave it False so that
      ``settings.forbid_external`` can block them.

    """
    settings = settings or Settings()
    if hasattr(url, "read"):
        content = url.read()
    else:
        if base_url:
            url = absolute_location(url, base_url)
        bundled = load_bundled_schema(url)
        if bundled is not None:
            return parse_xml(bundled, transport, base_url, settings=settings)
        if not _initial and settings.forbid_external:
            if urlparse(str(url)).scheme in ("http", "https"):
                raise ExternalReferenceForbidden(url)
        content = await transport.load(url)
    return parse_xml(content, transport, base_url, settings=settings)


def normalize_location(settings, url, base_url):
    """Return a 'normalized' url for the given url.

    This will make the url absolute and force it to https when that setting is
    enabled.

    """
    if base_url:
        url = absolute_location(url, base_url)

    if base_url and settings.force_https:
        base_url_parts = urlparse(base_url)
        url_parts = urlparse(url)
        if (
            base_url_parts.netloc == url_parts.netloc
            and base_url_parts.scheme != url_parts.scheme
        ):
            url = urlunparse(("https",) + url_parts[1:])
    return url


def absolute_location(location, base):
    """Make an url absolute (if it is optional) via the passed base url.

    :param location: The (relative) url
    :type location: str
    :param base: The base location
    :type base: str
    :returns: An absolute URL
    :rtype: str

    """
    if location == base:
        return location

    if urlparse(location).scheme in ("http", "https", "file"):
        return location

    if base and urlparse(base).scheme in ("http", "https", "file"):
        return urljoin(base, location)
    else:
        if os.path.isabs(location):
            return location
        if base:
            return os.path.realpath(os.path.join(os.path.dirname(base), location))
    return location


def is_relative_path(value):
    """Check if the given value is a relative path

    :param value: The value
    :type value: str
    :returns: Boolean indicating if the url is relative. If it is absolute then
      False is returned.
    :rtype: boolean

    """
    if urlparse(value).scheme in ("http", "https", "file"):
        return False
    return not os.path.isabs(value)
