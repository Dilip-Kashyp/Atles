import logging
from typing import Any
from app.mcp.client import MCPClient
from app.tools.base import BaseTool

log = logging.getLogger(__name__)


class MCPToolProxy(BaseTool):
    def __init__(self, mcp_client: MCPClient, name: str, description: str, input_schema: dict[str, Any]) -> None:
        self._mcp_client = mcp_client
        self._name = name
        self._description = description
        self._input_schema = input_schema

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict[str, Any]:
        return self._input_schema

    async def execute(self, arguments: dict[str, Any]) -> str:
        log.info("[CHECKPOINT: MCP_PROXY_EXECUTE] Forwarding '%s' to MCP server", self._name)
        return await self._mcp_client.call_tool(self._name, arguments)
