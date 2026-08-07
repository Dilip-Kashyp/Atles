"""
Infrastructure security: Fernet-based symmetric encryption.

Used exclusively for encrypting OAuth tokens at rest in oauth_accounts.
Never used for passwords (use bcrypt) or JWTs (use HMAC-SHA256).

The Fernet key is derived deterministically from ATLAS_MASTER_KEY using SHA-256,
then base64-encoded to satisfy Fernet's key format requirement.
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import get_settings


def _derive_fernet_key(master_key: str) -> bytes:
    """Derive a 32-byte Fernet-compatible key from the master key."""
    key_bytes = master_key.encode("utf-8")
    key_hash = hashlib.sha256(key_bytes).digest()
    return base64.urlsafe_b64encode(key_hash)


def _get_fernet(master_key: str | None = None) -> Fernet:
    settings = get_settings()
    key = master_key or settings.atlas_master_key
    if not key:
        raise RuntimeError("ATLAS_MASTER_KEY is not set — cannot encrypt/decrypt tokens.")
    return Fernet(_derive_fernet_key(key))


def encrypt(plaintext: str, master_key: str | None = None) -> bytes:
    """
    Encrypt a plaintext string using Fernet (AES-128-CBC + HMAC).

    Returns raw bytes suitable for storage in a BYTEA column.
    Raises ValueError if plaintext is empty.
    """
    if not plaintext:
        raise ValueError("Cannot encrypt an empty string.")
    return _get_fernet(master_key).encrypt(plaintext.encode("utf-8"))


def decrypt(ciphertext: bytes, master_key: str | None = None) -> str:
    """
    Decrypt Fernet-encrypted bytes back to a plaintext string.

    Raises cryptography.fernet.InvalidToken if the key is wrong or data is corrupted.
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt empty ciphertext.")
    return _get_fernet(master_key).decrypt(ciphertext).decode("utf-8")
