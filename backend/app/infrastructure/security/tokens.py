"""
Infrastructure security: JWT access token management.

Access tokens are short-lived (15 minutes) JWTs signed with HMAC-SHA256.
They carry ONLY the user_id (sub) and session_id — no user data.

Refresh tokens are NOT JWTs. They are opaque random strings stored as
SHA-256 hashes in the refresh_tokens table. See hashing.py and SessionService.

Token payload structure:
    {
        "sub": "<user_uuid>",
        "sid": "<session_uuid>",
        "type": "access",
        "exp": <unix_timestamp>,
        "iat": <unix_timestamp>,
    }
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.config import get_settings
from app.infrastructure.security.hashing import generate_secure_token

_ACCESS_TOKEN_EXPIRE_MINUTES = 15
_ALGORITHM = "HS256"


def _get_secret_key() -> str:
    secret = get_settings().atlas_master_key
    if not secret:
        raise RuntimeError("ATLAS_MASTER_KEY is not configured — cannot sign JWTs.")
    return secret


def create_access_token(user_id: str, session_id: str) -> str:
    """
    Create a signed JWT access token.

    Args:
        user_id: Atlas user UUID as string.
        session_id: Active session UUID as string (enables server-side revocation check on refresh).

    Returns:
        Signed JWT string valid for ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "sid": session_id,
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=_ALGORITHM)


def verify_access_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT access token.

    Returns:
        Decoded payload dict with 'sub' (user_id) and 'sid' (session_id),
        or None if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None
