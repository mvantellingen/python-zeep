from tests.utils import DummyTransport

from zeep.loader import parse_xml
from zeep.settings import Settings


def test_huge_text():
    # libxml2>=2.7.3 has XML_MAX_TEXT_LENGTH 10000000 without XML_PARSE_HUGE
    settings = Settings(xml_huge_tree=True)
    tree = parse_xml(u"""
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
         <s:Body>
          <HugeText xmlns="http://hugetext">%s</HugeText>
         </s:Body>
        </s:Envelope>
    """ % (u'\u00e5' * 10000001), DummyTransport(), settings=settings)

    assert tree[0][0].text == u'\u00e5' * 10000001
