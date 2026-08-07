from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Any

from app.memory.models import SessionContext

log = logging.getLogger(__name__)


class RuntimeCache:
    def __init__(self, max_size: int = 256, ttl_seconds: int = 3600) -> None:
        self._max_size   = max_size
        self._ttl        = ttl_seconds
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get_session(self, session_key: str) -> SessionContext | None:
        entry = self._store.get(session_key)
        if entry is None:
            return None

        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[session_key]
            log.debug("[CACHE_EXPIRE] session_key=%s", session_key)
            return None

        self._store.move_to_end(session_key)
        log.debug("[CACHE_HIT] session_key=%s", session_key)
        return value

    def set_session(self, session_key: str, ctx: SessionContext) -> None:
        expires_at = time.monotonic() + self._ttl

        if session_key in self._store:
            self._store.move_to_end(session_key)
        elif len(self._store) >= self._max_size:
            evicted_key, _ = self._store.popitem(last=False)
            log.debug("[CACHE_EVICT_LRU] evicted session_key=%s", evicted_key)

        self._store[session_key] = (ctx, expires_at)
        log.debug("[CACHE_SET] session_key=%s ttl=%ds", session_key, self._ttl)
