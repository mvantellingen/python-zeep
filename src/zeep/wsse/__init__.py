from .compose import Compose
from .signature import BinarySignature, MemorySignature, Signature
from .username import UsernameToken

try:
    from .crypto import (
        CryptoBinaryMemorySignature,
        CryptoBinarySignature,
        CryptoMemorySignature,
        CryptoSignature,
        PKCS12Signature,
    )
except ImportError:
    # cryptography not installed — pure-python signing unavailable
    CryptoBinaryMemorySignature = None
    CryptoBinarySignature = None
    CryptoMemorySignature = None
    CryptoSignature = None
    PKCS12Signature = None

__all__ = [
    "Compose",
    "BinarySignature",
    "MemorySignature",
    "Signature",
    "UsernameToken",
    "CryptoBinaryMemorySignature",
    "CryptoBinarySignature",
    "CryptoMemorySignature",
    "CryptoSignature",
    "PKCS12Signature",
]
