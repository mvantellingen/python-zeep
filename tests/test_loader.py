import pytest

from tests.utils import DummyTransport
from zeep.exceptions import DTDForbidden, EntitiesForbidden, ExternalReferenceForbidden
from zeep.loader import BUNDLED_SCHEMAS, load_external, parse_xml
from zeep.settings import Settings


def test_huge_text():
    # libxml2>=2.7.3 has XML_MAX_TEXT_LENGTH 10000000 without XML_PARSE_HUGE
    settings = Settings(xml_huge_tree=True)
    tree = parse_xml(
        """
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
         <s:Body>
          <HugeText xmlns="http://hugetext">%s</HugeText>
         </s:Body>
        </s:Envelope>
    """
        % ("\u00e5" * 10000001),
        DummyTransport(),
        settings=settings,
    )

    assert tree[0][0].text == "\u00e5" * 10000001


def test_allow_entities_and_dtd():
    xml = """
        <!DOCTYPE Author [
          <!ENTITY writer "Donald Duck.">
        ]>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
         <s:Body>
            <Author>&writer;</Author>
         </s:Body>
        </s:Envelope>
    """
    # DTD is allowed by default in defusexml so we follow this behaviour
    with pytest.raises(DTDForbidden):
        parse_xml(xml, DummyTransport(), settings=Settings(forbid_dtd=True))

    with pytest.raises(EntitiesForbidden):
        parse_xml(xml, DummyTransport())

    tree = parse_xml(xml, DummyTransport(), settings=Settings(forbid_entities=False))

    assert tree[0][0].tag == "Author"


def test_forbid_external_blocks_transitive_http_load():
    transport = DummyTransport()
    transport.bind("http://example.com/a.xsd", b"<root/>")

    with pytest.raises(ExternalReferenceForbidden):
        load_external(
            "http://example.com/a.xsd",
            transport,
            settings=Settings(forbid_external=True),
        )


def test_forbid_external_allows_initial_load():
    transport = DummyTransport()
    transport.bind("http://example.com/a.xsd", b"<root/>")

    tree = load_external(
        "http://example.com/a.xsd",
        transport,
        settings=Settings(forbid_external=True),
        _initial=True,
    )
    assert tree.tag == "root"


def test_forbid_external_default_allows_load():
    transport = DummyTransport()
    transport.bind("http://example.com/a.xsd", b"<root/>")

    tree = load_external("http://example.com/a.xsd", transport)
    assert tree.tag == "root"


@pytest.mark.parametrize(
    "url",
    [
        "http://schemas.xmlsoap.org/soap/encoding/",
        "https://schemas.xmlsoap.org/soap/encoding/",
    ],
)
def test_load_external_uses_bundled_soap_encoding_schema(url):
    # Nothing is bound on the transport and remote loads are forbidden, so
    # only the copy shipped with zeep can be used (#1417)
    settings = Settings(forbid_external=True)
    tree = load_external(url, DummyTransport(), settings=settings)
    assert tree.get("targetNamespace") == "http://schemas.xmlsoap.org/soap/encoding/"


def test_missing_bundled_schema_falls_back_to_transport(monkeypatch):
    # Packagers like PyInstaller can leave out the package data
    url = "http://schemas.xmlsoap.org/soap/encoding/"
    monkeypatch.setitem(BUNDLED_SCHEMAS, url, "missing.xsd")
    transport = DummyTransport()
    transport.bind(url, b"<root/>")
    assert load_external(url, transport).tag == "root"
