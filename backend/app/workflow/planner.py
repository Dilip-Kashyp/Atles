from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.workflow.states import ConversationState, StructuredContext

log = logging.getLogger(__name__)


class Planner:
    """Builds a simple generic plan from user text and context."""

    def build_plan(self, state: ConversationState) -> ConversationState:
        text = state.input_text.strip()
        lower = text.lower()

        if re.search(r"create|open|new", lower) and re.search(r"issue|ticket", lower):
            repo_match = re.search(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", text)
            plan = {
                "action": "create_issue",
                "tool": "create_issue",
                "arguments": {
                    "repo": repo_match.group(1) if repo_match else "owner/repo",
                    "title": text[:80].strip() or "Issue created from conversation",
                    "body": text,
                },
            }
        else:
            plan = {"action": "respond", "tool": None}

        state.plan = plan
        state.structured_context = StructuredContext(
            workspace_id=state.structured_context.workspace_id,
            channel_id=state.structured_context.channel_id,
            thread_id=state.structured_context.thread_id,
            user_id=state.structured_context.user_id,
            conversation_summary=state.structured_context.conversation_summary,
            intent=("create_issue" if plan["tool"] else "respond"),
            metadata={"raw_text": text},
        )
        log.info("[PLANNER] Built plan %s", json.dumps(plan))
        return state
