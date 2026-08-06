from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class Summarizer:
    """Simple deterministic summarizer for conversations."""

    async def summarize(self, messages: list[dict[str, Any]]) -> str:
        if not messages:
            return "No messages available"

        snippets = [item.get("text", "").strip() for item in messages if item.get("text")]
        if not snippets:
            return "No message content available"

        joined = " \n".join(snippets[-5:])
        return f"Conversation summary: {joined[:500]}"
