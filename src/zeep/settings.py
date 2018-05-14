import attr

from contextlib import contextmanager


@attr.s(slots=True)
class Settings(object):
    """

    :param xml_huge_tree: disable lxml/libxml2 security restrictions and
                          support very deep trees and very long text content
    :param strict: boolean to indicate if the lxml should be parsed a 'strict'.
      If false then the recover mode is enabled which tries to parse invalid
      XML as best as it can.
    :type strict: boolean
    :param forbid_dtd: disallow XML with a <!DOCTYPE> processing instruction
    :type forbid_dtd: bool
    :param forbid_entities: disallow XML with <!ENTITY> declarations inside the DTD
    :type forbid_entities: bool
    :param forbid_external: disallow any access to remote or local resources
      in external entities or DTD and raising an ExternalReferenceForbidden
      exception when a DTD or entity references an external resource.
    :type forbid_entities: bool
    :param force_https: Force all connections to HTTPS if the WSDL is also
      loaded from an HTTPS endpoint. (default: true)
    :type force_https: bool

    """
    xml_huge_tree = attr.ib(default=False)
    strict = attr.ib(default=True)
    raw_response = attr.ib(default=False)
    forbid_dtd = attr.ib(default=False)
    forbid_entities = attr.ib(default=True)
    forbid_external = attr.ib(default=True)
    force_https = attr.ib(default=True)

    @contextmanager
    def __call__(self, **options):
        current = {}
        for key, value in options.items():
            current[key] = getattr(self, key)
            setattr(self, key, value)

        yield

        for key, value in current.items():
            setattr(self, key, value)
