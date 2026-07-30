import logging
from typing import Any

from app.mcp.client import MCPClient
from app.tools.base import BaseTool
from app.tools.slack import MCPToolProxy

log = logging.getLogger(__name__)


class ToolDispatcher:
    def __init__(self) -> None:
        self._registry: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._registry[tool.name] = tool
        log.info("[CHECKPOINT: TOOL_REGISTERED] Tool '%s' registered", tool.name)

    async def register_mcp_client_tools(self, mcp_client: MCPClient) -> None:
        mcp_tools = await mcp_client.list_tools()
        for t in mcp_tools:
            proxy = MCPToolProxy(
                mcp_client=mcp_client,
                name=t.name,
                description=t.description or "",
                input_schema=dict(t.inputSchema) if t.inputSchema else {},
            )
            self.register(proxy)

    def get_all_tools(self) -> list[BaseTool]:
        return list(self._registry.values())

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if tool_name not in self._registry:
            log.error("[CHECKPOINT: TOOL_NOT_FOUND] '%s' not in registry", tool_name)
            raise ValueError(f"Tool '{tool_name}' not found in registry.")

        log.info("[CHECKPOINT: TOOL_EXECUTE_START] Invoking '%s' with args: %s", tool_name, arguments)
        tool = self._registry[tool_name]
        result = await tool.execute(arguments)
        log.info("[CHECKPOINT: TOOL_EXECUTE_DONE] '%s' completed (%d chars)", tool_name, len(result))
        return result
