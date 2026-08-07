"""Unit tests for JWT token generation and validation."""
from uuid import uuid4

from app.infrastructure.security import tokens


def test_create_and_verify_access_token():
    user_id = str(uuid4())
    session_id = str(uuid4())

    token = tokens.create_access_token(user_id=user_id, session_id=session_id)
    assert isinstance(token, str)

    payload = tokens.verify_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["sid"] == session_id
    assert payload["type"] == "access"


def test_verify_invalid_token():
    payload = tokens.verify_access_token("invalid.jwt.string")
    assert payload is None
