"""
Infrastructure cache: async Redis client.

Redis is used ONLY for:
- OAuth state (ephemeral, 10-min TTL)
- Rate limiting (sliding window counters)
- Permission caching (5-min TTL)
- One-time codes (e.g., future MFA)

Business entities are NEVER stored in Redis.
"""
import redis.asyncio as aioredis

from app.config import get_settings

_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """
    Return the singleton async Redis client.

    Lazily initialized on first call. Uses connection pooling internally.
    """
    global _client
    if _client is None:
        settings = get_settings()
        _client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
            max_connections=50,
        )
    return _client


# Convenience alias used throughout the codebase
redis_client = get_redis_client()
