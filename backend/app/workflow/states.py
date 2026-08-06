from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StructuredContext:
    """Simple structured context used by the planner/workflow layer."""

    workspace_id: str | None = None
    channel_id: str | None = None
    thread_id: str | None = None
    user_id: str | None = None
    conversation_summary: str | None = None
    intent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """Conversation state that can be passed through the workflow engine."""

    input_text: str
    structured_context: StructuredContext = field(default_factory=StructuredContext)
    plan: dict[str, Any] | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    result: str | None = None
    error: str | None = None
