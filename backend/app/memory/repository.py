"""
app/memory/repository.py
────────────────────────
Async MongoDB repository for the memory system.
Handles all database I/O for three collections:
  • sessions       — current working state per conversation
  • memories       — durable knowledge documents
  • slack_threads  — Slack thread metadata (no message content)

Uses motor (async pymongo) — the standard asyncio MongoDB driver.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from app.memory.models import Memory, SessionContext, SlackThreadMeta, WorkingState

log = logging.getLogger(__name__)


class MemoryRepository:
    """
    Thin async repository wrapping three MongoDB collections.

    Parameters
    ----------
    mongo_uri:
        Full MongoDB connection string (e.g. mongodb+srv://...).
    db_name:
        Database name. Defaults to "ai_teammate".
    """

    def __init__(self, mongo_uri: str, db_name: str = "ai_teammate") -> None:
        self._client = AsyncIOMotorClient(mongo_uri)
        self._db     = self._client[db_name]
        self._sessions      = self._db["sessions"]
        self._memories      = self._db["memories"]
        self._slack_threads = self._db["slack_threads"]

    async def ensure_indexes(self) -> None:
        """Create indexes on startup. Safe to call repeatedly (idempotent)."""
        # sessions: unique on session_key; TTL after 7 days inactivity
        await self._sessions.create_index("session_key", unique=True)
        await self._sessions.create_index(
            "updated_at",
            expireAfterSeconds=7 * 24 * 3600,  # 7 days
        )

        # memories: by session + recency; by session + type
        await self._memories.create_index([("session_key", 1), ("created_at", -1)])
        await self._memories.create_index([("session_key", 1), ("memory_type", 1)])

        # slack_threads: unique compound on thread_ts + channel_id
        await self._slack_threads.create_index(
            [("thread_ts", 1), ("channel_id", 1)],
            unique=True,
        )

        log.info("[CHECKPOINT: MEMORY_REPO_INDEXES] MongoDB indexes ensured")

    async def disconnect(self) -> None:
        """Close the MongoDB connection."""
        self._client.close()
        log.info("[CHECKPOINT: MEMORY_REPO_CLOSE] MongoDB connection closed")

    # ── Sessions ───────────────────────────────────────────────────────────────

    async def load_session(self, session_key: str) -> SessionContext | None:
        """Load a session document from MongoDB. Returns None if not found."""
        doc: dict[str, Any] | None = await self._sessions.find_one(
            {"session_key": session_key},
            {"_id": 0},
        )
        if doc is None:
            return None
        try:
            return SessionContext.model_validate(doc)
        except Exception as exc:
            log.warning("[MEMORY_REPO] Failed to parse session doc: %s", exc)
            return None

    async def upsert_session(self, ctx: SessionContext) -> None:
        """Insert or replace a session document atomically."""
        ctx.updated_at = datetime.now(timezone.utc)
        data = ctx.model_dump(mode="json")
        await self._sessions.update_one(
            {"session_key": ctx.session_key},
            {"$set": data},
            upsert=True,
        )
        log.debug("[MEMORY_REPO] Session upserted: %s", ctx.session_key)

    # ── Memories ───────────────────────────────────────────────────────────────

    async def save_memory(self, memory: Memory) -> None:
        """Persist a new memory document."""
        data = memory.model_dump(mode="json")
        await self._memories.insert_one(data)
        log.debug(
            "[MEMORY_REPO] Memory saved: type=%s session=%s",
            memory.memory_type,
            memory.session_key,
        )

    async def find_memories(
        self,
        session_key: str,
        limit: int = 5,
        memory_type: str | None = None,
    ) -> list[Memory]:
        """Retrieve the most recent memories for a session, newest first."""
        query: dict[str, Any] = {"session_key": session_key}
        if memory_type:
            query["memory_type"] = memory_type

        cursor = (
            self._memories
            .find(query, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        result: list[Memory] = []
        for doc in docs:
            try:
                result.append(Memory.model_validate(doc))
            except Exception as exc:
                log.warning("[MEMORY_REPO] Failed to parse memory doc: %s", exc)
        return result

    # ── Slack Threads ──────────────────────────────────────────────────────────

    async def upsert_slack_thread(self, meta: SlackThreadMeta) -> None:
        """Insert or update Slack thread metadata."""
        meta.updated_at = datetime.now(timezone.utc)
        data = meta.model_dump(mode="json")
        await self._slack_threads.update_one(
            {"thread_ts": meta.thread_ts, "channel_id": meta.channel_id},
            {"$set": data},
            upsert=True,
        )
        log.debug(
            "[MEMORY_REPO] Slack thread upserted: channel=%s thread=%s",
            meta.channel_id,
            meta.thread_ts,
        )

    async def find_slack_thread(
        self, thread_ts: str, channel_id: str
    ) -> SlackThreadMeta | None:
        """Retrieve stored metadata for a Slack thread."""
        doc = await self._slack_threads.find_one(
            {"thread_ts": thread_ts, "channel_id": channel_id},
            {"_id": 0},
        )
        if doc is None:
            return None
        try:
            return SlackThreadMeta.model_validate(doc)
        except Exception as exc:
            log.warning("[MEMORY_REPO] Failed to parse slack_thread doc: %s", exc)
            return None
