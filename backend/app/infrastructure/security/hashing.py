"""
Infrastructure security: cryptographic hashing for tokens.

Used for:
- Refresh token hashing (SHA-256) — stored in refresh_tokens.token_hash
- API key hashing (SHA-256) — stored in api_keys.key_hash
- Workspace invitation token hashing — stored in workspace_invitations.token_hash

Raw tokens are NEVER stored. Only hashes are persisted.
On lookup, hash the incoming token and compare with the stored hash.
"""
import hashlib
import hmac
import secrets


def hash_token(raw_token: str) -> str:
    """
    Produce a hex-encoded SHA-256 hash of a raw token string.

    This is a one-way operation. Use this result as the database lookup key.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_secure_token(nbytes: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Returns a URL-safe base64-encoded string (no padding).
    Default 32 bytes → 43-char string.
    """
    return secrets.token_urlsafe(nbytes)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.

    Always use this when comparing secrets.
    """
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
