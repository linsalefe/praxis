"""Criptografia AEAD de campos PII com Fernet.

`PRAXIS_FIELD_KEY` deve ser uma chave Fernet (32 bytes url-safe base64).
Gere com: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
"""
from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import get_settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    return Fernet(get_settings().field_key.encode())


def encrypt_str(value: str | None) -> bytes | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode("utf-8"))


def decrypt_str(value: bytes | None) -> str | None:
    if value is None:
        return None
    return _fernet().decrypt(bytes(value)).decode("utf-8")


def encrypt_bytes(value: bytes | None) -> bytes | None:
    """AEAD Fernet para blobs binários (PDFs, etc.)."""
    if value is None:
        return None
    return _fernet().encrypt(value)


def decrypt_bytes(value: bytes | None) -> bytes | None:
    if value is None:
        return None
    return _fernet().decrypt(bytes(value))
