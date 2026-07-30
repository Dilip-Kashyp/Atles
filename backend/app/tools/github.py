from typing import Any
from app.tools.base import BaseTool


class GithubIssueTool(BaseTool):
    """Tool for creating GitHub issues."""

    @property
    def name(self) -> str:
        return "open_issue"

    @property
    def description(self) -> str:
        return "Creates a new issue in the specified GitHub repository."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["repo", "title", "body"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        raise NotImplementedError("GitHub tool integration not yet wired into orchestrator registry.")
