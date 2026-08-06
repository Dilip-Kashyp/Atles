from __future__ import annotations

import json
from typing import Any

from app.tools.github import GithubIssueTool


class GitHubIssueProvider:
    """Stateless issue provider that adapts the GitHub tool for the workflow layer."""

    def __init__(self, token: str) -> None:
        self._tool = GithubIssueTool(token=token)

    async def create_issue(self, arguments: dict[str, Any]) -> str:
        return await self._tool.execute(arguments)

    async def execute(self, action: str, arguments: dict[str, Any]) -> str:
        if action != "create_issue":
            raise ValueError(f"Unsupported action: {action}")
        return await self.create_issue(arguments)
