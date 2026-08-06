from __future__ import annotations

import inspect
import json
import logging
from typing import Any

from app.models.chat import Conversation, Message
from app.models.tenancy import Workspace

log = logging.getLogger(__name__)


class ConversationLoader:
    """Load conversation threads into the persistence model."""

    def __init__(self, db_session: Any) -> None:
        self._db = db_session

    async def load(self, workspace_id: str, platform: str, external_thread_id: str, channel_id: str, messages: list[dict[str, Any]]) -> Conversation:
        workspace_result = self._db.get(Workspace, workspace_id)
        if inspect.isawaitable(workspace_result):
            workspace = await workspace_result
        else:
            workspace = workspace_result

        if workspace is None:
            raise ValueError(f"Workspace {workspace_id} not found")

        conversation = Conversation(
            workspace_id=workspace_id,
            platform=platform,
            external_thread_id=external_thread_id,
            channel_id=channel_id,
            title=(messages[0].get("text") if messages else None),
        )
        self._db.add(conversation)

        flush_result = self._db.flush()
        if inspect.isawaitable(flush_result):
            await flush_result

        for item in messages:
            message = Message(
                conversation_id=conversation.id,
                external_message_id=item.get("id"),
                author_id=item.get("user_id") or "system",
                content=item.get("text") or "",
                msg_metadata=item.get("metadata") or {},
            )
            self._db.add(message)

        commit_result = self._db.commit()
        if inspect.isawaitable(commit_result):
            await commit_result
        return conversation
