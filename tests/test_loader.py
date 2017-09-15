from defusedxml import EntitiesForbidden, DTDForbidden
from pytest import raises as assert_raises

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


def test_allow_entities_and_dtd():
    xml = u"""
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
    assert_raises(DTDForbidden, parse_xml, xml, DummyTransport(), forbid_dtd=True)
    assert_raises(EntitiesForbidden, parse_xml, xml, DummyTransport())

    tree = parse_xml(xml, DummyTransport(), forbid_entities=False)

    assert tree[0][0].tag == 'Author'
