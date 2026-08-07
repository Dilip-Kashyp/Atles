from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.workflow.states import ConversationState

log = logging.getLogger(__name__)


class WorkflowEngine:
    """Minimal workflow engine with validation, logging, and error handling."""

    def __init__(self, tool_registry: dict[str, Callable[..., Any]] | None = None) -> None:
        self._tool_registry = tool_registry or {}

    async def execute(self, state: ConversationState) -> ConversationState:
        if not state.input_text.strip():
            state.error = "Input text is empty"
            return state

        log.info("[WORKFLOW] Starting execution for %s", state.input_text[:80])
        try:
            if state.plan is None:
                state.plan = {"action": "respond", "tool": None}

            tool_name = state.plan.get("tool")
            if tool_name and tool_name in self._tool_registry:
                state.tool_name = tool_name
                state.tool_arguments = state.plan.get("arguments", {})
                state.result = await self._tool_registry[tool_name](state.tool_arguments)
            else:
                state.result = "No workflow action required"
        except Exception as exc:  
            state.error = str(exc)
            log.exception("[WORKFLOW] Execution failed")

        return state
