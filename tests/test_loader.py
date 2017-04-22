from zeep.loader import parse_xml
from tests.utils import DummyTransport

def test_huge_text():
    # libxml2>=2.7.3 has XML_MAX_TEXT_LENGTH 10000000 without XML_PARSE_HUGE
    tree = parse_xml(u"""
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
         <s:Body>
          <HugeText xmlns="http://hugetext">%s</HugeText>
         </s:Body>
        </s:Envelope>
    """ % (u'\u00e5' * 10000001), DummyTransport(), xml_huge_tree=True)

    assert tree[0][0].text == u'\u00e5' * 10000001
