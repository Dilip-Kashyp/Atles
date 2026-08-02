"""
app/memory/cache.py
───────────────────
Lightweight in-memory LRU cache for active sessions.
NOT the source of truth — that is MongoDB.
Reduces MongoDB round-trips for hot sessions.

Uses Python's built-in collections.OrderedDict for O(1) LRU eviction.
No external dependencies. Thread-safe for asyncio single-event-loop use.
"""
from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Any

from app.memory.models import SessionContext

log = logging.getLogger(__name__)


class RuntimeCache:
    """
    LRU cache for SessionContext objects.

    Parameters
    ----------
    max_size:
        Maximum number of sessions held in memory simultaneously.
        When the limit is reached, the least recently accessed session is evicted.
    ttl_seconds:
        Number of seconds a cached entry lives before expiring.
        Expiry is checked lazily on access (no background sweep thread needed).
    """

    def __init__(self, max_size: int = 256, ttl_seconds: int = 3600) -> None:
        self._max_size   = max_size
        self._ttl        = ttl_seconds
        # OrderedDict stores (value, expires_at) tuples; most-recently-used at end
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_session(self, session_key: str) -> SessionContext | None:
        """Return the cached SessionContext or None on miss / expiry."""
        entry = self._store.get(session_key)
        if entry is None:
            return None

        value, expires_at = entry
        if time.monotonic() > expires_at:
            # Stale entry — evict and treat as miss
            del self._store[session_key]
            log.debug("[CACHE_EXPIRE] session_key=%s", session_key)
            return None

        # Move to end (mark as most-recently-used)
        self._store.move_to_end(session_key)
        log.debug("[CACHE_HIT] session_key=%s", session_key)
        return value

    def set_session(self, session_key: str, ctx: SessionContext) -> None:
        """Insert or refresh a SessionContext. Evicts LRU entry if at capacity."""
        expires_at = time.monotonic() + self._ttl

        if session_key in self._store:
            self._store.move_to_end(session_key)
        elif len(self._store) >= self._max_size:
            evicted_key, _ = self._store.popitem(last=False)  # Remove LRU (front)
            log.debug("[CACHE_EVICT_LRU] evicted session_key=%s", evicted_key)

        self._store[session_key] = (ctx, expires_at)
        log.debug("[CACHE_SET] session_key=%s ttl=%ds", session_key, self._ttl)

    def invalidate(self, session_key: str) -> None:
        """Explicitly evict a session from the cache (e.g. on session close)."""
        if session_key in self._store:
            del self._store[session_key]
            log.debug("[CACHE_INVALIDATE] session_key=%s", session_key)

    def size(self) -> int:
        """Return the current number of entries in the cache."""
        return len(self._store)
