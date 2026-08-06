from __future__ import annotations

from typing import Any

from app.orchestrator.provider import GitHubIssueProvider
from app.workflow.engine import WorkflowEngine
from app.workflow.planner import Planner
from app.workflow.states import ConversationState
from app.workflow.tool_registry import ToolRegistry


class WorkflowBridge:
    """Bridge the workflow engine with the tool provider layer."""

    def __init__(self, github_provider: GitHubIssueProvider | None = None) -> None:
        self._registry = ToolRegistry()
        self._planner = Planner()
        self._engine = WorkflowEngine(tool_registry={})
        self._github_provider = github_provider

        if github_provider is not None:
            self._registry.register("create_issue", github_provider.create_issue)
            self._engine = WorkflowEngine(tool_registry=self._registry.as_dict())

    async def run(self, text: str, context: dict[str, Any] | None = None) -> ConversationState:
        state = ConversationState(input_text=text)
        if context:
            state.structured_context.metadata.update(context)
        state = self._planner.build_plan(state)
        return await self._engine.execute(state)
