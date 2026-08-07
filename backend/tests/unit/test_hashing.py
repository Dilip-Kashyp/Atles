"""Unit tests for cryptographic hashing utility."""
from app.infrastructure.security import hashing


def test_hash_token_deterministic():
    token = "secret-token-123"
    hash1 = hashing.hash_token(token)
    hash2 = hashing.hash_token(token)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex string length


def test_hash_token_unique():
    h1 = hashing.hash_token("token-a")
    h2 = hashing.hash_token("token-b")
    assert h1 != h2


def test_generate_secure_token():
    t1 = hashing.generate_secure_token(32)
    t2 = hashing.generate_secure_token(32)
    assert t1 != t2
    assert len(t1) > 30


def test_constant_time_compare():
    assert hashing.constant_time_compare("abc", "abc") is True
    assert hashing.constant_time_compare("abc", "xyz") is False
