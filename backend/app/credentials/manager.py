import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import get_settings

settings = get_settings()


class CredentialManager:
    """Encrypt and decrypt integration credentials using AES-GCM via Fernet."""

    def __init__(self, master_key: str | None = None) -> None:
        self._master_key = master_key or settings.atlas_master_key

    def _get_fernet(self) -> Fernet:
        key_bytes = self._master_key.encode("utf-8")
        key_hash = hashlib.sha256(key_bytes).digest()
        base64_key = base64.urlsafe_b64encode(key_hash)
        return Fernet(base64_key)

    def encrypt(self, secret: str) -> bytes:
        if not secret:
            raise ValueError("Cannot encrypt an empty secret.")
        return self._get_fernet().encrypt(secret.encode("utf-8"))

    def decrypt(self, encrypted_secret: bytes) -> str:
        if not encrypted_secret:
            raise ValueError("Cannot decrypt an empty secret.")
        return self._get_fernet().decrypt(encrypted_secret).decode("utf-8")


def encrypt_token(token: str) -> bytes:
    return CredentialManager().encrypt(token)


def decrypt_token(encrypted_token: bytes) -> str:
    return CredentialManager().decrypt(encrypted_token)
