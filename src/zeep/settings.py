import attr

from contextlib import contextmanager


@attr.s(slots=True)
class Settings(object):
    """

    :param xml_huge_tree: disable lxml/libxml2 security restrictions and
                          support very deep trees and very long text content

    """
    xml_huge_tree = attr.ib(default=False)
    strict = attr.ib(default=True)
    raw_response = attr.ib(default=False)

    @contextmanager
    def __call__(self, **options):
        current = {}
        for key, value in options.items():
            current[key] = getattr(self, key)
            setattr(self, key, value)

        yield

        for key, value in current.items():
            setattr(self, key, value)
