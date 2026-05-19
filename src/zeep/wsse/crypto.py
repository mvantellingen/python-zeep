"""Pure-Python WS-Security (WSSE) signature creation and verification.

This module provides the same functionality as ``zeep.wsse.signature`` but uses
the ``cryptography`` library instead of the C-based ``xmlsec`` library. This
makes installation straightforward on all platforms—no system-level C libraries
required.

Key improvements over the xmlsec-based module:

* **No C dependencies** — only ``cryptography`` and ``lxml`` (both are
  pure-Python wheels on all major platforms).
* **PKCS#12 key support** — load keys from ``.p12`` / ``.pfx`` files directly.
* **Configurable signed parts** — sign Body, Timestamp, UsernameToken,
  BinarySecurityToken, or any element with a ``wsu:Id``.
* **Inclusive namespace prefixes** — per-reference control over exclusive C14N
  ``InclusiveNamespaces/PrefixList``, required by some government SOAP services.
* **Mixed algorithms** — e.g. SHA-256 digests with RSA-SHA1 signature, a
  common requirement of older WS-Security profiles.

Usage::

    from zeep.wsse.crypto import CryptoSignature, CryptoBinarySignature

    # PEM files — drop-in replacement for wsse.Signature / wsse.BinarySignature
    sig = CryptoSignature("key.pem", "cert.pem")
    sig = CryptoBinarySignature("key.pem", "cert.pem")

    # PKCS#12 — pass raw bytes or a file path
    sig = CryptoBinarySignature.from_pkcs12("cert.p12", b"password")

    # Sign extra elements and control C14N prefixes
    sig = CryptoBinarySignature(
        "key.pem", "cert.pem",
        sign_username_token=True,
        sign_binary_security_token=True,
        inclusive_ns_prefixes={"Body": ["wsse", "ds"]},
    )

"""

import base64
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from lxml import etree
from lxml.etree import QName

from zeep import ns
from zeep.exceptions import SignatureVerificationFailed
from zeep.utils import detect_soap_env
from zeep.wsse.utils import ensure_id, get_security_header

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa, utils
    from cryptography.hazmat.primitives.serialization.pkcs12 import (
        load_key_and_certificates,
    )
    from cryptography.x509.oid import ExtensionOID
    from cryptography.x509 import load_der_x509_certificate, load_pem_x509_certificate
except ImportError:
    hashes = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Algorithm URI constants
# ---------------------------------------------------------------------------

# Signature algorithms
SIG_RSA_SHA1 = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
SIG_RSA_SHA256 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
SIG_RSA_SHA384 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha384"
SIG_RSA_SHA512 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha512"

# Digest algorithms
DIGEST_SHA1 = "http://www.w3.org/2000/09/xmldsig#sha1"
DIGEST_SHA256 = "http://www.w3.org/2001/04/xmlenc#sha256"
DIGEST_SHA384 = "http://www.w3.org/2001/04/xmldsig-more#sha384"
DIGEST_SHA512 = "http://www.w3.org/2001/04/xmlenc#sha512"

# Canonicalization
C14N_EXCL = "http://www.w3.org/2001/10/xml-exc-c14n#"
KEY_IDENTIFIER_SKI = "ski"
KEY_IDENTIFIER_THUMBPRINT = "thumbprint"
KEY_INFO_X509 = "x509"
KEY_INFO_BINARY_REF = "binary-ref"

# Mapping from URI → cryptography hash class
_SIG_HASH_MAP = {
    SIG_RSA_SHA1: hashes.SHA1 if hashes else None,
    SIG_RSA_SHA256: hashes.SHA256 if hashes else None,
    SIG_RSA_SHA384: hashes.SHA384 if hashes else None,
    SIG_RSA_SHA512: hashes.SHA512 if hashes else None,
}

_DIGEST_HASH_MAP = {
    DIGEST_SHA1: hashlib.sha1,
    DIGEST_SHA256: hashlib.sha256,
    DIGEST_SHA384: hashlib.sha384,
    DIGEST_SHA512: hashlib.sha512,
}


def _check_crypto_import():
    if hashes is None:
        raise ImportError(
            "The cryptography module is required for CryptoSignature().\nInstall it with: pip install cryptography\n"
        )


def _read_file(f_name):
    with open(f_name, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Key / certificate loading
# ---------------------------------------------------------------------------


def _load_pem_private_key(key_data: bytes, password: Optional[bytes] = None):
    """Load an RSA private key from PEM-encoded data."""
    return serialization.load_pem_private_key(key_data, password=password)


def _load_pem_certificate(cert_data: bytes):
    """Load an X.509 certificate from PEM-encoded data."""
    return load_pem_x509_certificate(cert_data)


def _load_pkcs12(p12_data: bytes, password: Optional[bytes] = None) -> Tuple[Any, Any, Any]:
    """Load private key, certificate, and additional certs from PKCS#12 data.

    Returns ``(private_key, certificate, additional_certs)``.
    """
    return load_key_and_certificates(p12_data, password)


def _cert_der_bytes(certificate) -> bytes:
    """Return the DER-encoded bytes of an X.509 certificate object."""
    return certificate.public_bytes(serialization.Encoding.DER)


def _cert_base64(certificate) -> str:
    """Return the base64-encoded DER representation of the certificate."""
    return base64.b64encode(_cert_der_bytes(certificate)).decode("ascii")


def _cert_thumbprint_sha1_base64(certificate) -> str:
    """Return base64(SHA1(DER(cert)))."""
    thumbprint = hashlib.sha1(_cert_der_bytes(certificate)).digest()
    return base64.b64encode(thumbprint).decode("ascii")


def _cert_subject_key_identifier_base64(certificate) -> str:
    """Return base64(subjectKeyIdentifier) from cert extension."""
    try:
        ski_ext = certificate.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_KEY_IDENTIFIER)
    except Exception:
        raise ValueError("Certificate does not contain SubjectKeyIdentifier extension")
    return base64.b64encode(ski_ext.value.digest).decode("ascii")


# ---------------------------------------------------------------------------
# XML canonicalization and digest helpers
# ---------------------------------------------------------------------------


def _c14n(element: etree._Element, inclusive_prefixes: Optional[List[str]] = None) -> bytes:
    """Exclusive C14N of *element* with optional inclusive namespace prefixes."""
    return etree.tostring(
        element,
        method="c14n",
        exclusive=True,
        inclusive_ns_prefixes=inclusive_prefixes,
        with_comments=False,
    )


def _compute_digest(
    element: etree._Element,
    digest_uri: str = DIGEST_SHA256,
    inclusive_prefixes: Optional[List[str]] = None,
) -> str:
    """Canonicalize *element* and return the base64-encoded digest."""
    c14n_bytes = _c14n(element, inclusive_prefixes)
    hash_fn = _DIGEST_HASH_MAP.get(digest_uri)
    if hash_fn is None:
        raise ValueError(f"Unsupported digest algorithm: {digest_uri}")
    digest = hash_fn(c14n_bytes).digest()
    return base64.b64encode(digest).decode("ascii")


def _sign_bytes(private_key, data: bytes, signature_uri: str = SIG_RSA_SHA1) -> bytes:
    """Sign *data* using *private_key* and the algorithm identified by *signature_uri*."""
    hash_cls = _SIG_HASH_MAP.get(signature_uri)
    if hash_cls is None:
        raise ValueError(f"Unsupported signature algorithm: {signature_uri}")
    return private_key.sign(data, padding.PKCS1v15(), hash_cls())


def _verify_bytes(public_key, signature_bytes: bytes, data: bytes, signature_uri: str):
    """Verify *signature_bytes* over *data*."""
    hash_cls = _SIG_HASH_MAP.get(signature_uri)
    if hash_cls is None:
        raise ValueError(f"Unsupported signature algorithm: {signature_uri}")
    public_key.verify(signature_bytes, data, padding.PKCS1v15(), hash_cls())


# ---------------------------------------------------------------------------
# DS namespace helpers
# ---------------------------------------------------------------------------

DS_NS = ns.DS


def _ds(tag):
    return QName(DS_NS, tag)


def _ec(tag):
    return QName(C14N_EXCL, tag)


def _wsse(tag):
    return QName(ns.WSSE, tag)


def _wsu(tag):
    return QName(ns.WSU, tag)


# ---------------------------------------------------------------------------
# Signature XML construction
# ---------------------------------------------------------------------------


def _build_reference(
    parent: etree._Element,
    uri: str,
    digest_value: str,
    digest_uri: str,
    inclusive_prefixes: Optional[List[str]] = None,
):
    """Append a ``ds:Reference`` element to *parent*."""
    ref = etree.SubElement(parent, _ds("Reference"), URI=uri)
    transforms = etree.SubElement(ref, _ds("Transforms"))
    transform = etree.SubElement(transforms, _ds("Transform"), Algorithm=C14N_EXCL)
    if inclusive_prefixes is not None:
        etree.SubElement(
            transform,
            _ec("InclusiveNamespaces"),
            PrefixList=" ".join(inclusive_prefixes),
        )
    etree.SubElement(ref, _ds("DigestMethod"), Algorithm=digest_uri)
    dv = etree.SubElement(ref, _ds("DigestValue"))
    dv.text = digest_value
    return ref


def _sign_envelope(
    envelope: etree._Element,
    private_key,
    certificate,
    signature_method: str = SIG_RSA_SHA1,
    digest_method: str = DIGEST_SHA1,
    sign_timestamp: bool = True,
    sign_username_token: bool = False,
    sign_binary_security_token: bool = False,
    extra_references: Optional[List[etree._Element]] = None,
    inclusive_ns_prefixes: Optional[Dict[str, List[str]]] = None,
    c14n_inclusive_prefixes: Optional[List[str]] = None,
) -> etree._Element:
    """Build a ``ds:Signature``, sign the envelope, and insert into the
    ``wsse:Security`` header.

    Parameters
    ----------
    envelope : lxml Element
        The SOAP envelope to sign.
    private_key :
        An RSA private key from the ``cryptography`` library.
    certificate :
        An X.509 certificate from the ``cryptography`` library.
    signature_method : str
        URI of the signature algorithm (default RSA-SHA1).
    digest_method : str
        URI of the digest algorithm (default SHA1).
    sign_timestamp : bool
        Whether to sign the ``wsu:Timestamp`` if present.
    sign_username_token : bool
        Whether to sign the ``wsse:UsernameToken`` if present.
    sign_binary_security_token : bool
        Whether to sign the ``wsse:BinarySecurityToken`` if present.
    extra_references : list, optional
        Additional elements to sign (must already have ``wsu:Id``).
    inclusive_ns_prefixes : dict, optional
        Mapping of element local-name → list of inclusive namespace prefixes
        for exclusive C14N.  E.g. ``{"Body": ["wsse", "ds"]}``.
    c14n_inclusive_prefixes : list, optional
        Default inclusive prefixes for the ``CanonicalizationMethod`` of
        ``SignedInfo`` itself.

    Returns
    -------
    The ``ds:Signature`` element that was inserted.
    """
    soap_env = detect_soap_env(envelope)
    security = get_security_header(envelope)
    body = envelope.find(QName(soap_env, "Body"))

    inc = inclusive_ns_prefixes or {}

    # ---- collect elements to sign ----
    targets: List[Tuple[etree._Element, Optional[List[str]]]] = []

    if body is not None:
        targets.append((body, inc.get("Body")))

    if sign_timestamp:
        ts = security.find(_wsu("Timestamp"))
        if ts is not None:
            targets.append((ts, inc.get("Timestamp")))

    if sign_username_token:
        ut = security.find(_wsse("UsernameToken"))
        if ut is not None:
            targets.append((ut, inc.get("UsernameToken")))

    if sign_binary_security_token:
        bst = security.find(_wsse("BinarySecurityToken"))
        if bst is not None:
            targets.append((bst, inc.get("BinarySecurityToken")))

    for extra in extra_references or []:
        local = QName(extra.tag).localname
        targets.append((extra, inc.get(local)))

    # ---- build ds:Signature skeleton ----
    sig_el = etree.SubElement(security, _ds("Signature"))
    signed_info = etree.SubElement(sig_el, _ds("SignedInfo"))

    # CanonicalizationMethod
    c14n_method = etree.SubElement(signed_info, _ds("CanonicalizationMethod"), Algorithm=C14N_EXCL)
    if c14n_inclusive_prefixes:
        etree.SubElement(
            c14n_method,
            _ec("InclusiveNamespaces"),
            PrefixList=" ".join(c14n_inclusive_prefixes),
        )

    # SignatureMethod
    etree.SubElement(signed_info, _ds("SignatureMethod"), Algorithm=signature_method)

    # ---- add references ----
    for target, prefixes in targets:
        node_id = ensure_id(target)
        digest_value = _compute_digest(target, digest_method, prefixes)
        _build_reference(
            signed_info,
            "#" + node_id,
            digest_value,
            digest_method,
            prefixes,
        )

    # ---- compute signature ----
    signed_info_c14n = _c14n(signed_info, c14n_inclusive_prefixes)
    raw_signature = _sign_bytes(private_key, signed_info_c14n, signature_method)

    sig_value = etree.SubElement(sig_el, _ds("SignatureValue"))
    sig_value.text = base64.b64encode(raw_signature).decode("ascii")

    return sig_el


def _add_key_info_x509(sig_el, certificate):
    """Add ``ds:KeyInfo`` with ``X509Data`` (issuer-serial + certificate)."""
    key_info = etree.SubElement(sig_el, _ds("KeyInfo"))
    sec_token_ref = etree.SubElement(key_info, _wsse("SecurityTokenReference"))
    x509_data = etree.SubElement(sec_token_ref, _ds("X509Data"))

    x509_issuer_serial = etree.SubElement(x509_data, _ds("X509IssuerSerial"))
    issuer_name = etree.SubElement(x509_issuer_serial, _ds("X509IssuerName"))
    issuer_name.text = certificate.issuer.rfc4514_string()
    serial_number = etree.SubElement(x509_issuer_serial, _ds("X509SerialNumber"))
    serial_number.text = str(certificate.serial_number)

    x509_cert = etree.SubElement(x509_data, _ds("X509Certificate"))
    x509_cert.text = _cert_base64(certificate)

    return key_info


def _add_key_info_binary_ref(sig_el, bintok_id):
    """Add ``ds:KeyInfo`` referencing a ``BinarySecurityToken`` by ``wsu:Id``."""
    key_info = etree.SubElement(sig_el, _ds("KeyInfo"))
    sec_token_ref = etree.SubElement(key_info, _wsse("SecurityTokenReference"))
    etree.SubElement(
        sec_token_ref,
        _wsse("Reference"),
        URI="#" + bintok_id,
        ValueType=("http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"),
    )
    return key_info


def _add_key_info_key_identifier(sig_el, certificate, identifier_type: str):
    """Add wsse:KeyIdentifier in SecurityTokenReference."""
    key_info = etree.SubElement(sig_el, _ds("KeyInfo"))
    sec_token_ref = etree.SubElement(key_info, _wsse("SecurityTokenReference"))

    if identifier_type == KEY_IDENTIFIER_THUMBPRINT:
        value_type = (
            "http://docs.oasis-open.org/wss/oasis-wss-soap-message-security-1.1#ThumbprintSHA1"
        )
        value = _cert_thumbprint_sha1_base64(certificate)
    elif identifier_type == KEY_IDENTIFIER_SKI:
        value_type = (
            "http://docs.oasis-open.org/wss/2004/01/"
            "oasis-200401-wss-x509-token-profile-1.0#X509SubjectKeyIdentifier"
        )
        value = _cert_subject_key_identifier_base64(certificate)
    else:
        raise ValueError(f"Unsupported key identifier type: {identifier_type}")

    key_id = etree.SubElement(
        sec_token_ref,
        _wsse("KeyIdentifier"),
        ValueType=value_type,
        EncodingType=(
            "http://docs.oasis-open.org/wss/2004/01/"
            "oasis-200401-wss-soap-message-security-1.0#Base64Binary"
        ),
    )
    key_id.text = value
    return key_info


def _add_binary_security_token(security, certificate):
    """Insert a ``BinarySecurityToken`` into the security header and return it."""
    bintok = etree.Element(
        _wsse("BinarySecurityToken"),
        {
            "ValueType": ("http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"),
            "EncodingType": (
                "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"
            ),
        },
    )
    ensure_id(bintok)
    bintok.text = _cert_base64(certificate)
    # Insert at position 0 (before Signature, Timestamp, etc.)
    security.insert(0, bintok)
    return bintok


def _reorder_security_children(security: etree._Element, layout: str):
    """Reorder wsse:Security direct children for interop-sensitive layouts."""
    if layout == "append":
        return

    layout_map = {
        "xmlsec_compatible": ["Signature", "BinarySecurityToken", "Timestamp"],
        "signature_first": ["Signature", "Timestamp", "BinarySecurityToken"],
        "timestamp_first": ["Timestamp", "BinarySecurityToken", "Signature"],
        "binary_first": ["BinarySecurityToken", "Timestamp", "Signature"],
    }
    priority = layout_map.get(layout)
    if priority is None:
        raise ValueError(f"Unsupported security_header_layout: {layout}")

    indexed = list(enumerate(list(security)))
    ranked = sorted(
        indexed,
        key=lambda item: (
            priority.index(QName(item[1].tag).localname)
            if QName(item[1].tag).localname in priority
            else len(priority),
            item[0],
        ),
    )

    for child in list(security):
        security.remove(child)
    for _, child in ranked:
        security.append(child)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _binary_security_token_id(bintok: etree._Element) -> Optional[str]:
    return bintok.get(QName(ns.WSU, "Id")) or bintok.get("Id")


def _resolve_binary_security_token(envelope, sig_el: etree._Element) -> etree._Element:
    """Resolve the BinarySecurityToken referenced by the signature KeyInfo."""
    key_info = sig_el.find(QName(ns.DS, "KeyInfo"))
    if key_info is None:
        raise SignatureVerificationFailed("No ds:KeyInfo found in Signature")

    references = key_info.xpath(".//wsse:Reference", namespaces={"wsse": ns.WSSE})
    for reference in references:
        uri = reference.get("URI", "")
        if not uri.startswith("#"):
            continue

        token_id = uri[1:]
        for bintok in envelope.xpath(
            "//wsse:BinarySecurityToken",
            namespaces={"wsse": ns.WSSE},
        ):
            if _binary_security_token_id(bintok) == token_id:
                return bintok

    raise SignatureVerificationFailed("Referenced wsse:BinarySecurityToken not found")


def _load_certificate_from_binary_security_token(envelope, sig_el: etree._Element):
    """Load the DER X.509 certificate embedded in the signature's BinarySecurityToken."""
    bintok = _resolve_binary_security_token(envelope, sig_el)
    if not bintok.text:
        raise SignatureVerificationFailed("wsse:BinarySecurityToken is empty")

    try:
        token_text = "".join(bintok.text.split())
        cert_der = base64.b64decode(token_text, validate=True)
        return load_der_x509_certificate(cert_der)
    except Exception:
        raise SignatureVerificationFailed("Invalid wsse:BinarySecurityToken certificate")


def _verify_envelope(envelope, certificate, use_binary_security_token: bool = False):
    """Verify a signed SOAP envelope using the given certificate."""
    soap_env = detect_soap_env(envelope)
    header = envelope.find(QName(soap_env, "Header"))
    if header is None:
        raise SignatureVerificationFailed("No SOAP Header found")

    security = header.find(QName(ns.WSSE, "Security"))
    if security is None:
        raise SignatureVerificationFailed("No wsse:Security header found")

    sig_el = security.find(QName(ns.DS, "Signature"))
    if sig_el is None:
        raise SignatureVerificationFailed("No ds:Signature found in Security header")

    signed_info = sig_el.find(QName(ns.DS, "SignedInfo"))
    sig_value_el = sig_el.find(QName(ns.DS, "SignatureValue"))
    if signed_info is None or sig_value_el is None:
        raise SignatureVerificationFailed("Malformed Signature element")

    if use_binary_security_token:
        certificate = _load_certificate_from_binary_security_token(envelope, sig_el)

    # Determine signature algorithm
    sig_method_el = signed_info.find(QName(ns.DS, "SignatureMethod"))
    signature_uri = sig_method_el.get("Algorithm") if sig_method_el is not None else SIG_RSA_SHA1

    # Get inclusive prefixes for SignedInfo canonicalization (if any)
    c14n_method = signed_info.find(QName(ns.DS, "CanonicalizationMethod"))
    c14n_prefixes = None
    if c14n_method is not None:
        inc_ns = c14n_method.find(_ec("InclusiveNamespaces"))
        if inc_ns is not None:
            prefix_list = inc_ns.get("PrefixList", "")
            c14n_prefixes = prefix_list.split() if prefix_list.strip() else None

    # Recompute SignedInfo canonical form
    signed_info_c14n = _c14n(signed_info, c14n_prefixes)

    # Decode signature value
    raw_signature = base64.b64decode(sig_value_el.text)

    # Verify the signature over SignedInfo
    public_key = certificate.public_key()
    try:
        _verify_bytes(public_key, raw_signature, signed_info_c14n, signature_uri)
    except Exception:
        raise SignatureVerificationFailed("Signature value verification failed")

    # Verify each reference digest
    refs = signed_info.findall(QName(ns.DS, "Reference"))
    for ref in refs:
        uri = ref.get("URI", "")
        if not uri.startswith("#"):
            continue

        ref_id = uri[1:]
        referenced = envelope.xpath("//*[@wsu:Id='%s']" % ref_id, namespaces={"wsu": ns.WSU})
        if not referenced:
            raise SignatureVerificationFailed(f"Referenced element not found: {ref_id}")

        element = referenced[0]

        # Get digest algorithm
        digest_method_el = ref.find(QName(ns.DS, "DigestMethod"))
        digest_uri = digest_method_el.get("Algorithm") if digest_method_el is not None else DIGEST_SHA1

        # Get inclusive prefixes from the transform
        inc_prefixes = None
        transforms = ref.find(QName(ns.DS, "Transforms"))
        if transforms is not None:
            for transform in transforms.findall(QName(ns.DS, "Transform")):
                inc_ns = transform.find(_ec("InclusiveNamespaces"))
                if inc_ns is not None:
                    prefix_list = inc_ns.get("PrefixList", "")
                    inc_prefixes = prefix_list.split() if prefix_list.strip() else None

        # Compute digest and compare
        computed_digest = _compute_digest(element, digest_uri, inc_prefixes)
        expected_digest_el = ref.find(QName(ns.DS, "DigestValue"))
        expected_digest = expected_digest_el.text if expected_digest_el is not None else ""

        if computed_digest != expected_digest:
            raise SignatureVerificationFailed(f"Digest mismatch for element {ref_id}")

    return certificate


def _parse_xs_datetime(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_timestamp_policy(
    envelope: etree._Element,
    now: Optional[datetime] = None,
    clock_skew_seconds: int = 0,
):
    """Validate Timestamp freshness semantics (Created/Expires)."""
    soap_env = detect_soap_env(envelope)
    header = envelope.find(QName(soap_env, "Header"))
    if header is None:
        raise SignatureVerificationFailed("No SOAP Header found")
    security = header.find(QName(ns.WSSE, "Security"))
    if security is None:
        raise SignatureVerificationFailed("No wsse:Security header found")
    timestamp = security.find(QName(ns.WSU, "Timestamp"))
    if timestamp is None:
        raise SignatureVerificationFailed("No wsu:Timestamp found")

    created_el = timestamp.find(QName(ns.WSU, "Created"))
    expires_el = timestamp.find(QName(ns.WSU, "Expires"))
    if created_el is None or created_el.text is None:
        raise SignatureVerificationFailed("Timestamp missing wsu:Created")
    if expires_el is None or expires_el.text is None:
        raise SignatureVerificationFailed("Timestamp missing wsu:Expires")

    created = _parse_xs_datetime(created_el.text)
    expires = _parse_xs_datetime(expires_el.text)
    if expires < created:
        raise SignatureVerificationFailed("Timestamp has Expires earlier than Created")

    now = now or datetime.now(timezone.utc)
    skew = abs(int(clock_skew_seconds))
    if created.timestamp() - skew > now.timestamp():
        raise SignatureVerificationFailed("Timestamp Created is in the future")
    if expires.timestamp() + skew < now.timestamp():
        raise SignatureVerificationFailed("Timestamp has expired")


def _validate_certificate_time(certificate, now: Optional[datetime] = None):
    """Validate certificate validity period against current time."""
    now = now or datetime.now(timezone.utc)
    not_before = getattr(certificate, "not_valid_before_utc", None)
    not_after = getattr(certificate, "not_valid_after_utc", None)
    if not_before is None:
        not_before = certificate.not_valid_before.replace(tzinfo=timezone.utc)
    if not_after is None:
        not_after = certificate.not_valid_after.replace(tzinfo=timezone.utc)

    if now < not_before:
        raise SignatureVerificationFailed("Certificate is not yet valid")
    if now > not_after:
        raise SignatureVerificationFailed("Certificate has expired")


# ---------------------------------------------------------------------------
# Public API — classes
# ---------------------------------------------------------------------------


class CryptoMemorySignature:
    """Sign a SOAP envelope using in-memory PEM key and certificate data.

    This is the pure-Python equivalent of :class:`zeep.wsse.signature.MemorySignature`.
    It uses the ``cryptography`` library instead of ``xmlsec``.

    Parameters
    ----------
    key_data : bytes
        PEM-encoded private key.
    cert_data : bytes
        PEM-encoded X.509 certificate.
    password : bytes or str, optional
        Password for the private key.
    signature_method : str, optional
        Signature algorithm URI (default: RSA-SHA1).
    digest_method : str, optional
        Digest algorithm URI (default: SHA1).
    sign_timestamp : bool
        Sign the ``wsu:Timestamp`` element if present (default True).
    sign_username_token : bool
        Sign the ``wsse:UsernameToken`` element if present (default False).
    sign_binary_security_token : bool
        Sign the ``wsse:BinarySecurityToken`` if present (default False).
    timestamp_token : lxml Element, optional
        ``wsu:Timestamp`` element to append to ``wsse:Security`` before signing.
    inclusive_ns_prefixes : dict, optional
        Element-name → prefix-list mapping for exclusive C14N.
    c14n_inclusive_prefixes : list, optional
        Inclusive prefixes for the ``CanonicalizationMethod`` of ``SignedInfo``.
    """

    def __init__(
        self,
        key_data: bytes,
        cert_data: bytes,
        password: Optional[Union[bytes, str]] = None,
        signature_method: str = SIG_RSA_SHA1,
        digest_method: str = DIGEST_SHA1,
        sign_timestamp: bool = True,
        sign_username_token: bool = False,
        sign_binary_security_token: bool = False,
        inclusive_ns_prefixes: Optional[Dict[str, List[str]]] = None,
        c14n_inclusive_prefixes: Optional[List[str]] = None,
        key_info_style: str = KEY_INFO_X509,
        security_header_layout: str = "append",
        timestamp_token: Optional[etree._Element] = None,
    ):
        _check_crypto_import()

        if isinstance(password, str):
            password = password.encode("utf-8")

        private_key = _load_pem_private_key(key_data, password)
        certificate = _load_pem_certificate(cert_data)
        self._configure(
            private_key,
            certificate,
            signature_method=signature_method,
            digest_method=digest_method,
            sign_timestamp=sign_timestamp,
            sign_username_token=sign_username_token,
            sign_binary_security_token=sign_binary_security_token,
            inclusive_ns_prefixes=inclusive_ns_prefixes,
            c14n_inclusive_prefixes=c14n_inclusive_prefixes,
            key_info_style=key_info_style,
            security_header_layout=security_header_layout,
            timestamp_token=timestamp_token,
        )

    def _configure(
        self,
        private_key,
        certificate,
        signature_method: str = SIG_RSA_SHA1,
        digest_method: str = DIGEST_SHA1,
        sign_timestamp: bool = True,
        sign_username_token: bool = False,
        sign_binary_security_token: bool = False,
        inclusive_ns_prefixes: Optional[Dict[str, List[str]]] = None,
        c14n_inclusive_prefixes: Optional[List[str]] = None,
        key_info_style: str = KEY_INFO_X509,
        security_header_layout: str = "append",
        timestamp_token: Optional[etree._Element] = None,
    ):
        """Assign all signing-related attributes."""
        self.private_key = private_key
        self.certificate = certificate
        self.signature_method = signature_method
        self.digest_method = digest_method
        self.sign_timestamp = sign_timestamp
        self.sign_username_token = sign_username_token
        self.sign_binary_security_token = sign_binary_security_token
        self.inclusive_ns_prefixes = inclusive_ns_prefixes
        self.c14n_inclusive_prefixes = c14n_inclusive_prefixes
        self.key_info_style = key_info_style
        self.security_header_layout = security_header_layout
        self.timestamp_token = timestamp_token

    def _append_timestamp_token(self, envelope):
        if self.timestamp_token is None:
            return
        security = get_security_header(envelope)
        security.append(self.timestamp_token)

    def _sign(self, envelope):
        """Sign the envelope and add KeyInfo with X509Data."""
        self._append_timestamp_token(envelope)
        sig_el = _sign_envelope(
            envelope,
            self.private_key,
            self.certificate,
            signature_method=self.signature_method,
            digest_method=self.digest_method,
            sign_timestamp=self.sign_timestamp,
            sign_username_token=self.sign_username_token,
            sign_binary_security_token=self.sign_binary_security_token,
            inclusive_ns_prefixes=self.inclusive_ns_prefixes,
            c14n_inclusive_prefixes=self.c14n_inclusive_prefixes,
        )
        if self.key_info_style == KEY_INFO_X509:
            _add_key_info_x509(sig_el, self.certificate)
        elif self.key_info_style in (KEY_IDENTIFIER_SKI, KEY_IDENTIFIER_THUMBPRINT):
            _add_key_info_key_identifier(sig_el, self.certificate, self.key_info_style)
        else:
            raise ValueError(f"Unsupported key_info_style: {self.key_info_style}")

        security = get_security_header(envelope)
        _reorder_security_children(security, self.security_header_layout)
        return sig_el

    def apply(self, envelope, headers):
        self._sign(envelope)
        return envelope, headers

    def verify(
        self,
        envelope,
        validate_timestamp: bool = False,
        clock_skew_seconds: int = 0,
        validate_certificate_time: bool = False,
        use_binary_security_token: bool = False,
        now: Optional[datetime] = None,
    ):
        certificate = _verify_envelope(
            envelope,
            self.certificate,
            use_binary_security_token=use_binary_security_token,
        )
        if validate_timestamp:
            _validate_timestamp_policy(
                envelope,
                now=now,
                clock_skew_seconds=clock_skew_seconds,
            )
        if validate_certificate_time:
            _validate_certificate_time(certificate, now=now)
        return envelope


class CryptoSignature(CryptoMemorySignature):
    """Sign a SOAP envelope using PEM key and certificate files.

    Drop-in replacement for :class:`zeep.wsse.signature.Signature`.

    Parameters
    ----------
    key_file : str
        Path to PEM private key file.
    certfile : str
        Path to PEM certificate file.
    password : bytes or str, optional
        Private key password.
    signature_method, digest_method, sign_timestamp, sign_username_token,
    sign_binary_security_token, inclusive_ns_prefixes, c14n_inclusive_prefixes :
        See :class:`CryptoMemorySignature`.
    """

    def __init__(
        self,
        key_file: str,
        certfile: str,
        password: Optional[Union[bytes, str]] = None,
        signature_method: str = SIG_RSA_SHA1,
        digest_method: str = DIGEST_SHA1,
        **kwargs,
    ):
        super().__init__(
            _read_file(key_file),
            _read_file(certfile),
            password,
            signature_method,
            digest_method,
            **kwargs,
        )


class CryptoBinaryMemorySignature(CryptoMemorySignature):
    """Sign a SOAP envelope and embed the certificate as a
    ``BinarySecurityToken``.

    This is the pure-Python equivalent of
    :class:`zeep.wsse.signature.BinarySignature`.

    The certificate is placed in a ``wsse:BinarySecurityToken`` element in the
    security header, and the ``ds:KeyInfo`` in the signature references it.
    """

    def _sign(self, envelope):
        security = get_security_header(envelope)
        self._append_timestamp_token(envelope)
        bintok = _add_binary_security_token(security, self.certificate)
        bintok_id = bintok.get(QName(ns.WSU, "Id"))

        sig_el = _sign_envelope(
            envelope,
            self.private_key,
            self.certificate,
            signature_method=self.signature_method,
            digest_method=self.digest_method,
            sign_timestamp=self.sign_timestamp,
            sign_username_token=self.sign_username_token,
            sign_binary_security_token=self.sign_binary_security_token,
            inclusive_ns_prefixes=self.inclusive_ns_prefixes,
            c14n_inclusive_prefixes=self.c14n_inclusive_prefixes,
        )
        _add_key_info_binary_ref(sig_el, bintok_id)
        _reorder_security_children(security, self.security_header_layout)
        return sig_el


class CryptoBinarySignature(CryptoBinaryMemorySignature):
    """Sign a SOAP envelope using PEM files and embed a ``BinarySecurityToken``.

    Drop-in replacement for :class:`zeep.wsse.signature.BinarySignature`.

    Parameters
    ----------
    key_file : str
        Path to PEM private key file.
    certfile : str
        Path to PEM certificate file.
    password : bytes or str, optional
        Private key password.
    signature_method, digest_method, sign_timestamp, sign_username_token,
    sign_binary_security_token, inclusive_ns_prefixes, c14n_inclusive_prefixes :
        See :class:`CryptoMemorySignature`.
    """

    def __init__(
        self,
        key_file: str,
        certfile: str,
        password: Optional[Union[bytes, str]] = None,
        signature_method: str = SIG_RSA_SHA1,
        digest_method: str = DIGEST_SHA1,
        **kwargs,
    ):
        super().__init__(
            _read_file(key_file),
            _read_file(certfile),
            password,
            signature_method,
            digest_method,
            **kwargs,
        )

    @classmethod
    def from_pkcs12(
        cls,
        p12_file: str,
        password: Optional[Union[bytes, str]] = None,
        signature_method: str = SIG_RSA_SHA1,
        digest_method: str = DIGEST_SHA1,
        **kwargs,
    ):
        """Create a ``CryptoBinarySignature`` from a PKCS#12 file.

        Parameters
        ----------
        p12_file : str
            Path to a ``.p12`` or ``.pfx`` file.
        password : bytes or str, optional
            Password for the PKCS#12 file.
        """
        _check_crypto_import()

        if isinstance(password, str):
            password = password.encode("utf-8")

        p12_data = _read_file(p12_file)
        private_key, certificate, _ = _load_pkcs12(p12_data, password)

        instance = cls.__new__(cls)
        instance._configure(
            private_key,
            certificate,
            signature_method=signature_method,
            digest_method=digest_method,
            **kwargs,
        )
        return instance


class PKCS12Signature(CryptoMemorySignature):
    """Sign a SOAP envelope using a PKCS#12 file with X509Data in KeyInfo.

    Parameters
    ----------
    p12_file : str
        Path to a ``.p12`` or ``.pfx`` file.
    password : bytes or str, optional
        Password for the PKCS#12 file.
    """

    def __init__(
        self,
        p12_file: str,
        password: Optional[Union[bytes, str]] = None,
        signature_method: str = SIG_RSA_SHA1,
        digest_method: str = DIGEST_SHA1,
        **kwargs,
    ):
        _check_crypto_import()

        if isinstance(password, str):
            password = password.encode("utf-8")

        p12_data = _read_file(p12_file)
        private_key, certificate, _ = _load_pkcs12(p12_data, password)

        self._configure(
            private_key,
            certificate,
            signature_method=signature_method,
            digest_method=digest_method,
            **kwargs,
        )
