from typing import Any
from app.tools.base import BaseTool


class NotionSearchTool(BaseTool):
    """Tool for searching Notion documentation."""

    @property
    def name(self) -> str:
        return "find_document"

    @property
    def description(self) -> str:
        return "Searches the Notion workspace for documentation matching the query."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        raise NotImplementedError("Notion tool integration not yet wired into orchestrator registry.")
