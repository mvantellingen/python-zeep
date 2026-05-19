"""Tests for zeep.wsse.crypto — pure-Python WS-Security signing."""

import os
from datetime import datetime, timezone

import pytest
from lxml import etree
from lxml.etree import QName
from zeep import ns
from zeep.exceptions import SignatureVerificationFailed
from zeep.wsse import crypto

from tests.utils import load_xml

TESTS_DIR = os.path.dirname(os.path.realpath(__file__))
KEY_FILE = os.path.join(TESTS_DIR, "test_key.pem")
CERT_FILE = os.path.join(TESTS_DIR, "test_cert.pem")
P12_FILE = os.path.join(TESTS_DIR, "test_cert.p12")
P12_PASSWORD = b"testpass"

# Also test with the repo's existing cert (combined key+cert PEM)
COMBINED_PEM = os.path.join(TESTS_DIR, "cert_valid.pem")
COMBINED_PEM_PW = os.path.join(TESTS_DIR, "cert_valid_pw.pem")

skip_if_no_crypto = pytest.mark.skipif(crypto.hashes is None, reason="cryptography library not installed")


def _make_envelope():
    return load_xml(
        """
        <soapenv:Envelope
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
          <soapenv:Header></soapenv:Header>
          <soapenv:Body>
            <tns:Function>
              <tns:Argument>OK</tns:Argument>
            </tns:Function>
          </soapenv:Body>
        </soapenv:Envelope>
    """
    )


def _make_envelope_with_timestamp():
    return load_xml(
        """
        <soapenv:Envelope
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
          <soapenv:Header
              xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
            <wsse:Security>
              <wsu:Timestamp
                  xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                <wsu:Created>2025-01-01T00:00:00Z</wsu:Created>
                <wsu:Expires>2025-01-01T01:00:00Z</wsu:Expires>
              </wsu:Timestamp>
            </wsse:Security>
          </soapenv:Header>
          <soapenv:Body>
            <tns:Function>
              <tns:Argument>OK</tns:Argument>
            </tns:Function>
          </soapenv:Body>
        </soapenv:Envelope>
    """
    )


def _make_envelope_with_username_token():
    return load_xml(
        """
        <soapenv:Envelope
            xmlns:tns="http://tests.python-zeep.org/"
            xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
            xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/">
          <soapenv:Header
              xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
            <wsse:Security>
              <wsu:Timestamp
                  xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                <wsu:Created>2025-01-01T00:00:00Z</wsu:Created>
                <wsu:Expires>2025-01-01T01:00:00Z</wsu:Expires>
              </wsu:Timestamp>
              <wsse:UsernameToken
                  xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
                <wsse:Username>testuser</wsse:Username>
                <wsse:Password>testpass</wsse:Password>
              </wsse:UsernameToken>
            </wsse:Security>
          </soapenv:Header>
          <soapenv:Body>
            <tns:Function>
              <tns:Argument>OK</tns:Argument>
            </tns:Function>
          </soapenv:Body>
        </soapenv:Envelope>
    """
    )


def _make_timestamp_token():
    timestamp = etree.Element(QName(ns.WSU, "Timestamp"), nsmap={"wsu": ns.WSU})
    created = etree.SubElement(timestamp, QName(ns.WSU, "Created"))
    created.text = "2025-01-01T00:00:00Z"
    expires = etree.SubElement(timestamp, QName(ns.WSU, "Expires"))
    expires.text = "2025-01-01T01:00:00Z"
    return timestamp


# -----------------------------------------------------------------------
# Basic signing & verification
# -----------------------------------------------------------------------


@skip_if_no_crypto
class TestCryptoSignature:
    """Tests for CryptoSignature (X509Data in KeyInfo)."""

    def test_sign_and_verify(self):
        envelope = _make_envelope()
        plugin = crypto.CryptoSignature(KEY_FILE, CERT_FILE)
        envelope, headers = plugin.apply(envelope, {})
        plugin.verify(envelope)

    def test_sign_with_timestamp(self):
        envelope = _make_envelope_with_timestamp()
        plugin = crypto.CryptoSignature(KEY_FILE, CERT_FILE)
        envelope, headers = plugin.apply(envelope, {})
        plugin.verify(envelope)

        # Should have 2 references: Body + Timestamp
        refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
        assert len(refs) == 2

    def test_verify_fails_on_tampered_body(self):
        envelope = _make_envelope()
        plugin = crypto.CryptoSignature(KEY_FILE, CERT_FILE)
        envelope, headers = plugin.apply(envelope, {})

        # Tamper with the body
        nsmap = {"tns": "http://tests.python-zeep.org/"}
        for elm in envelope.xpath("//tns:Argument", namespaces=nsmap):
            elm.text = "TAMPERED"

        with pytest.raises(SignatureVerificationFailed):
            plugin.verify(envelope)

    def test_combined_pem(self):
        """Test with a PEM file containing both key and cert."""
        envelope = _make_envelope()
        plugin = crypto.CryptoSignature(COMBINED_PEM, COMBINED_PEM)
        envelope, headers = plugin.apply(envelope, {})
        plugin.verify(envelope)

    def test_combined_pem_with_password(self):
        envelope = _make_envelope()
        plugin = crypto.CryptoSignature(COMBINED_PEM_PW, COMBINED_PEM_PW, "geheim")
        envelope, headers = plugin.apply(envelope, {})
        plugin.verify(envelope)

    def test_x509_data_present(self):
        """Verify KeyInfo contains X509Data with certificate."""
        envelope = _make_envelope()
        plugin = crypto.CryptoSignature(KEY_FILE, CERT_FILE)
        envelope, headers = plugin.apply(envelope, {})

        x509_cert = envelope.xpath(
            "//ds:KeyInfo//ds:X509Certificate",
            namespaces={"ds": ns.DS},
        )
        assert len(x509_cert) == 1
        assert x509_cert[0].text  # Certificate should be non-empty


# -----------------------------------------------------------------------
# BinarySignature
# -----------------------------------------------------------------------


@skip_if_no_crypto
class TestCryptoBinarySignature:
    """Tests for CryptoBinarySignature (BinarySecurityToken in header)."""

    def test_sign_and_verify(self):
        envelope = _make_envelope()
        plugin = crypto.CryptoBinarySignature(KEY_FILE, CERT_FILE)
        envelope, headers = plugin.apply(envelope, {})
        plugin.verify(envelope)

    def test_binary_token_present(self):
        envelope = _make_envelope()
        plugin = crypto.CryptoBinarySignature(KEY_FILE, CERT_FILE)
        envelope, headers = plugin.apply(envelope, {})

        bintok = envelope.xpath(
            "//wsse:BinarySecurityToken",
            namespaces={"wsse": ns.WSSE},
        )
        assert len(bintok) == 1
        assert bintok[0].text  # Should contain base64 cert

    def test_key_info_references_binary_token(self):
        envelope = _make_envelope()
        plugin = crypto.CryptoBinarySignature(KEY_FILE, CERT_FILE)
        envelope, headers = plugin.apply(envelope, {})

        bintok = envelope.xpath(
            "//wsse:BinarySecurityToken",
            namespaces={"wsse": ns.WSSE},
        )[0]
        ref = envelope.xpath(
            "//ds:KeyInfo//wsse:Reference",
            namespaces={"ds": ns.DS, "wsse": ns.WSSE},
        )[0]
        bintok_id = bintok.get(QName(ns.WSU, "Id"))
        assert ref.get("URI") == "#" + bintok_id

    def test_sign_with_timestamp(self):
        envelope = _make_envelope_with_timestamp()
        plugin = crypto.CryptoBinarySignature(KEY_FILE, CERT_FILE)
        envelope, headers = plugin.apply(envelope, {})
        plugin.verify(envelope)

        refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
        assert len(refs) == 2

    def test_verify_fails_on_tampered_body(self):
        envelope = _make_envelope()
        plugin = crypto.CryptoBinarySignature(KEY_FILE, CERT_FILE)
        envelope, headers = plugin.apply(envelope, {})

        nsmap = {"tns": "http://tests.python-zeep.org/"}
        for elm in envelope.xpath("//tns:Argument", namespaces=nsmap):
            elm.text = "TAMPERED"

        with pytest.raises(SignatureVerificationFailed):
            plugin.verify(envelope)

    def test_verify_with_binary_security_token_opt_in(self):
        envelope = _make_envelope()
        signer = crypto.CryptoBinarySignature(KEY_FILE, CERT_FILE)
        envelope, headers = signer.apply(envelope, {})

        verifier = crypto.CryptoSignature(COMBINED_PEM, COMBINED_PEM)
        with pytest.raises(SignatureVerificationFailed):
            verifier.verify(envelope)

        verifier.verify(envelope, use_binary_security_token=True)

    def test_verify_with_binary_security_token_fails_on_tampered_body(self):
        envelope = _make_envelope()
        signer = crypto.CryptoBinarySignature(KEY_FILE, CERT_FILE)
        envelope, headers = signer.apply(envelope, {})

        nsmap = {"tns": "http://tests.python-zeep.org/"}
        for elm in envelope.xpath("//tns:Argument", namespaces=nsmap):
            elm.text = "TAMPERED"

        verifier = crypto.CryptoSignature(COMBINED_PEM, COMBINED_PEM)
        with pytest.raises(SignatureVerificationFailed):
            verifier.verify(envelope, use_binary_security_token=True)

    def test_verify_with_binary_security_token_missing_token_raises(self):
        envelope = _make_envelope()
        signer = crypto.CryptoBinarySignature(KEY_FILE, CERT_FILE)
        envelope, headers = signer.apply(envelope, {})

        bintok = envelope.xpath(
            "//wsse:BinarySecurityToken",
            namespaces={"wsse": ns.WSSE},
        )[0]
        bintok.getparent().remove(bintok)

        with pytest.raises(SignatureVerificationFailed):
            signer.verify(envelope, use_binary_security_token=True)

    def test_verify_with_binary_security_token_malformed_token_raises(self):
        envelope = _make_envelope()
        signer = crypto.CryptoBinarySignature(KEY_FILE, CERT_FILE)
        envelope, headers = signer.apply(envelope, {})

        bintok = envelope.xpath(
            "//wsse:BinarySecurityToken",
            namespaces={"wsse": ns.WSSE},
        )[0]
        bintok.text = "not-base64"

        with pytest.raises(SignatureVerificationFailed):
            signer.verify(envelope, use_binary_security_token=True)


# -----------------------------------------------------------------------
# Algorithm combinations
# -----------------------------------------------------------------------

SIGNATURE_METHODS = [
    (crypto.SIG_RSA_SHA1, "http://www.w3.org/2000/09/xmldsig#rsa-sha1"),
    (crypto.SIG_RSA_SHA256, "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"),
]

DIGEST_METHODS = [
    (crypto.DIGEST_SHA1, "http://www.w3.org/2000/09/xmldsig#sha1"),
    (crypto.DIGEST_SHA256, "http://www.w3.org/2001/04/xmlenc#sha256"),
]


@skip_if_no_crypto
@pytest.mark.parametrize("sig_method,expected_sig_href", SIGNATURE_METHODS)
@pytest.mark.parametrize("digest_method,expected_digest_href", DIGEST_METHODS)
def test_algorithm_combinations(sig_method, expected_sig_href, digest_method, expected_digest_href):
    """Test all combinations of signature and digest algorithms."""
    envelope = _make_envelope_with_timestamp()
    plugin = crypto.CryptoSignature(
        KEY_FILE,
        CERT_FILE,
        signature_method=sig_method,
        digest_method=digest_method,
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    # Verify algorithm URIs in the XML
    digests = envelope.xpath("//ds:DigestMethod", namespaces={"ds": ns.DS})
    assert len(digests) > 0
    for d in digests:
        assert d.get("Algorithm") == expected_digest_href

    signatures = envelope.xpath("//ds:SignatureMethod", namespaces={"ds": ns.DS})
    assert len(signatures) == 1
    assert signatures[0].get("Algorithm") == expected_sig_href


@skip_if_no_crypto
def test_mixed_algorithms_sha256_digest_sha1_signature():
    """VetStat-style: SHA256 digests with RSA-SHA1 signature."""
    envelope = _make_envelope_with_timestamp()
    plugin = crypto.CryptoSignature(
        KEY_FILE,
        CERT_FILE,
        signature_method=crypto.SIG_RSA_SHA1,
        digest_method=crypto.DIGEST_SHA256,
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    digests = envelope.xpath("//ds:DigestMethod", namespaces={"ds": ns.DS})
    for d in digests:
        assert d.get("Algorithm") == crypto.DIGEST_SHA256

    sig_method = envelope.xpath("//ds:SignatureMethod", namespaces={"ds": ns.DS})[0]
    assert sig_method.get("Algorithm") == crypto.SIG_RSA_SHA1


@skip_if_no_crypto
def test_key_identifier_thumbprint():
    envelope = _make_envelope()
    plugin = crypto.CryptoSignature(
        KEY_FILE,
        CERT_FILE,
        key_info_style=crypto.KEY_IDENTIFIER_THUMBPRINT,
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    key_identifier = envelope.xpath(
        "//ds:KeyInfo//wsse:KeyIdentifier",
        namespaces={"ds": ns.DS, "wsse": ns.WSSE},
    )
    assert len(key_identifier) == 1
    assert key_identifier[0].get("ValueType").endswith("ThumbprintSHA1")
    assert key_identifier[0].text


@skip_if_no_crypto
def test_key_identifier_ski():
    envelope = _make_envelope()
    plugin = crypto.CryptoSignature(
        KEY_FILE,
        CERT_FILE,
        key_info_style=crypto.KEY_IDENTIFIER_SKI,
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    key_identifier = envelope.xpath(
        "//ds:KeyInfo//wsse:KeyIdentifier",
        namespaces={"ds": ns.DS, "wsse": ns.WSSE},
    )
    assert len(key_identifier) == 1
    assert key_identifier[0].get("ValueType").endswith("X509SubjectKeyIdentifier")
    assert key_identifier[0].text


# -----------------------------------------------------------------------
# Signing extra elements (UsernameToken, BinarySecurityToken)
# -----------------------------------------------------------------------


@skip_if_no_crypto
def test_sign_username_token():
    """Sign Body + Timestamp + UsernameToken."""
    envelope = _make_envelope_with_username_token()
    plugin = crypto.CryptoSignature(
        KEY_FILE,
        CERT_FILE,
        sign_username_token=True,
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
    assert len(refs) == 3  # Body + Timestamp + UsernameToken


@skip_if_no_crypto
def test_sign_binary_security_token():
    """Sign Body + Timestamp + BinarySecurityToken."""
    envelope = _make_envelope_with_timestamp()
    plugin = crypto.CryptoBinarySignature(
        KEY_FILE,
        CERT_FILE,
        sign_binary_security_token=True,
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
    assert len(refs) == 3  # Body + Timestamp + BinarySecurityToken


@skip_if_no_crypto
def test_sign_all_elements():
    """VetStat-style: sign Body + Timestamp + UsernameToken + BinarySecurityToken."""
    envelope = _make_envelope_with_username_token()
    plugin = crypto.CryptoBinarySignature(
        KEY_FILE,
        CERT_FILE,
        sign_username_token=True,
        sign_binary_security_token=True,
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
    assert len(refs) == 4  # Body + Timestamp + UsernameToken + BinarySecurityToken


# -----------------------------------------------------------------------
# Inclusive namespace prefixes
# -----------------------------------------------------------------------


@skip_if_no_crypto
def test_inclusive_ns_prefixes():
    """Verify that inclusive namespace prefixes appear in the transform elements."""
    envelope = _make_envelope_with_timestamp()
    plugin = crypto.CryptoSignature(
        KEY_FILE,
        CERT_FILE,
        inclusive_ns_prefixes={
            "Body": ["wsse", "ds"],
            "Timestamp": ["soapenv", "wsse"],
        },
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    # Find InclusiveNamespaces elements
    inc_ns_els = envelope.xpath(
        "//ds:Reference/ds:Transforms/ds:Transform/ec:InclusiveNamespaces",
        namespaces={
            "ds": ns.DS,
            "ec": "http://www.w3.org/2001/10/xml-exc-c14n#",
        },
    )
    assert len(inc_ns_els) >= 1
    prefix_lists = [el.get("PrefixList") for el in inc_ns_els]
    assert "wsse ds" in prefix_lists or "ds wsse" in prefix_lists


@skip_if_no_crypto
def test_security_header_layout_xmlsec_compatible():
    envelope = _make_envelope_with_timestamp()
    plugin = crypto.CryptoBinarySignature(
        KEY_FILE,
        CERT_FILE,
        security_header_layout="xmlsec_compatible",
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    security_children = envelope.xpath(
        "//wsse:Security/*",
        namespaces={"wsse": ns.WSSE},
    )
    local_names = [QName(node.tag).localname for node in security_children]
    assert local_names[:3] == ["Signature", "BinarySecurityToken", "Timestamp"]


@skip_if_no_crypto
def test_c14n_inclusive_prefixes_on_signed_info():
    """Verify CanonicalizationMethod has inclusive prefixes when configured."""
    envelope = _make_envelope()
    plugin = crypto.CryptoSignature(
        KEY_FILE,
        CERT_FILE,
        c14n_inclusive_prefixes=["ds", "ec", "soapenv", "wsse", "wsu"],
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    c14n_method = envelope.xpath(
        "//ds:SignedInfo/ds:CanonicalizationMethod",
        namespaces={"ds": ns.DS},
    )[0]
    inc_ns = c14n_method.find(QName("http://www.w3.org/2001/10/xml-exc-c14n#", "InclusiveNamespaces"))
    assert inc_ns is not None
    assert "ds" in inc_ns.get("PrefixList")


# -----------------------------------------------------------------------
# PKCS#12 support
# -----------------------------------------------------------------------


@skip_if_no_crypto
def test_pkcs12_signature():
    """Test PKCS12Signature with .p12 file."""
    envelope = _make_envelope()
    plugin = crypto.PKCS12Signature(P12_FILE, P12_PASSWORD)
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)


@skip_if_no_crypto
def test_binary_signature_from_pkcs12():
    """Test CryptoBinarySignature.from_pkcs12 classmethod."""
    envelope = _make_envelope()
    plugin = crypto.CryptoBinarySignature.from_pkcs12(P12_FILE, P12_PASSWORD)
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)


@skip_if_no_crypto
def test_pkcs12_with_timestamp():
    envelope = _make_envelope_with_timestamp()
    plugin = crypto.PKCS12Signature(P12_FILE, P12_PASSWORD)
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
    assert len(refs) == 2


@skip_if_no_crypto
def test_pkcs12_string_password():
    """Test that string passwords are accepted."""
    envelope = _make_envelope()
    plugin = crypto.PKCS12Signature(P12_FILE, "testpass")
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)


# -----------------------------------------------------------------------
# Compose with UsernameToken
# -----------------------------------------------------------------------


@skip_if_no_crypto
def test_compose_with_username_token():
    """Test using Compose to combine UsernameToken + CryptoSignature."""
    from zeep.wsse import Compose
    from zeep.wsse.username import UsernameToken

    envelope = _make_envelope()
    wsse_plugin = Compose(
        [
            UsernameToken("testuser", "testpass"),
            crypto.CryptoSignature(KEY_FILE, CERT_FILE),
        ]
    )
    envelope, headers = wsse_plugin.apply(envelope, {})

    # Should have the username token
    ut = envelope.xpath(
        "//wsse:UsernameToken/wsse:Username",
        namespaces={"wsse": ns.WSSE},
    )
    assert len(ut) == 1
    assert ut[0].text == "testuser"

    # Should have a signature
    sig = envelope.xpath("//ds:Signature", namespaces={"ds": ns.DS})
    assert len(sig) == 1


@skip_if_no_crypto
def test_compose_username_and_signed_username():
    """Compose UsernameToken + CryptoBinarySignature that also signs the token."""
    from zeep.wsse import Compose
    from zeep.wsse.username import UsernameToken

    envelope = _make_envelope()
    wsse_plugin = Compose(
        [
            UsernameToken("testuser", "testpass"),
            crypto.CryptoBinarySignature(
                KEY_FILE,
                CERT_FILE,
                sign_username_token=True,
            ),
        ]
    )
    envelope, headers = wsse_plugin.apply(envelope, {})

    # Should have refs for Body + UsernameToken (no Timestamp in this envelope)
    refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
    assert len(refs) == 2


# -----------------------------------------------------------------------
# Memory-based classes
# -----------------------------------------------------------------------


@skip_if_no_crypto
def test_memory_signature():
    """Test CryptoMemorySignature with raw PEM bytes."""
    with open(KEY_FILE, "rb") as f:
        key_data = f.read()
    with open(CERT_FILE, "rb") as f:
        cert_data = f.read()

    envelope = _make_envelope()
    plugin = crypto.CryptoMemorySignature(key_data, cert_data)
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)


@skip_if_no_crypto
def test_binary_memory_signature():
    """Test CryptoBinaryMemorySignature with raw PEM bytes."""
    with open(KEY_FILE, "rb") as f:
        key_data = f.read()
    with open(CERT_FILE, "rb") as f:
        cert_data = f.read()

    envelope = _make_envelope()
    plugin = crypto.CryptoBinaryMemorySignature(key_data, cert_data)
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    bintok = envelope.xpath(
        "//wsse:BinarySecurityToken",
        namespaces={"wsse": ns.WSSE},
    )
    assert len(bintok) == 1


# -----------------------------------------------------------------------
# Edge cases
# -----------------------------------------------------------------------


@skip_if_no_crypto
def test_no_timestamp_only_body():
    """When there's no Timestamp, should only sign Body."""
    envelope = _make_envelope()
    plugin = crypto.CryptoSignature(KEY_FILE, CERT_FILE)
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
    assert len(refs) == 1  # Body only


@skip_if_no_crypto
def test_sign_timestamp_disabled():
    """Explicitly disable timestamp signing."""
    envelope = _make_envelope_with_timestamp()
    plugin = crypto.CryptoSignature(
        KEY_FILE,
        CERT_FILE,
        sign_timestamp=False,
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
    assert len(refs) == 1  # Body only


@skip_if_no_crypto
def test_timestamp_token_is_appended_and_signed():
    """A provided Timestamp token is appended before signing."""
    envelope = _make_envelope()
    plugin = crypto.CryptoSignature(
        KEY_FILE,
        CERT_FILE,
        timestamp_token=_make_timestamp_token(),
    )
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope)

    timestamps = envelope.xpath("//wsu:Timestamp", namespaces={"wsu": ns.WSU})
    assert len(timestamps) == 1

    refs = envelope.xpath("//ds:Reference", namespaces={"ds": ns.DS})
    assert len(refs) == 2  # Body + appended Timestamp


@skip_if_no_crypto
def test_verify_no_header_raises():
    """Verify raises on envelope without Header."""
    envelope = load_xml(
        """
        <soapenv:Envelope
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
          <soapenv:Body><data/></soapenv:Body>
        </soapenv:Envelope>
        """
    )
    with pytest.raises(SignatureVerificationFailed):
        crypto._verify_envelope(
            envelope,
            crypto._load_pem_certificate(open(CERT_FILE, "rb").read()),
        )


@skip_if_no_crypto
def test_verify_no_security_header_raises():
    """Verify raises on envelope with Header but no Security."""
    envelope = load_xml(
        """
        <soapenv:Envelope
            xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
          <soapenv:Header></soapenv:Header>
          <soapenv:Body><data/></soapenv:Body>
        </soapenv:Envelope>
        """
    )
    with pytest.raises(SignatureVerificationFailed):
        crypto._verify_envelope(
            envelope,
            crypto._load_pem_certificate(open(CERT_FILE, "rb").read()),
        )


@skip_if_no_crypto
def test_verify_with_timestamp_policy_expired_raises():
    envelope = _make_envelope_with_timestamp()
    plugin = crypto.CryptoSignature(KEY_FILE, CERT_FILE)
    envelope, headers = plugin.apply(envelope, {})

    with pytest.raises(SignatureVerificationFailed):
        plugin.verify(
            envelope,
            validate_timestamp=True,
            now=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )


@skip_if_no_crypto
def test_verify_with_certificate_time_policy_passes():
    envelope = _make_envelope()
    plugin = crypto.CryptoSignature(KEY_FILE, CERT_FILE)
    envelope, headers = plugin.apply(envelope, {})
    plugin.verify(envelope, validate_certificate_time=True)
