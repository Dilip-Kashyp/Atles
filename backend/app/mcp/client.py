import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

log = logging.getLogger(__name__)

MCP_INIT_TIMEOUT = 30


class MCPClient:
    def __init__(self, server_script: str, extra_env: dict[str, str] | None = None) -> None:
        self._server_script = server_script
        self._extra_env = extra_env or {}
        self._stdio_context: Any = None
        self._session_context: Any = None
        self.session: ClientSession | None = None

    async def __aenter__(self) -> "MCPClient":
        await self._connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._disconnect()

    async def _connect(self) -> None:
        project_root = Path(__file__).resolve().parent.parent.parent
        server_path = project_root / self._server_script

        if not server_path.exists():
            raise FileNotFoundError(f"MCP server script not found at: {server_path}")

        log.info("[CHECKPOINT: MCP_SUBPROCESS_START] %s", server_path.name)
        env = {**os.environ, **self._extra_env}

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(server_path)],
            env=env,
        )

        self._stdio_context = stdio_client(server_params)
        read, write = await self._stdio_context.__aenter__()

        self._session_context = ClientSession(read, write)
        self.session = await self._session_context.__aenter__()

        try:
            await asyncio.wait_for(self.session.initialize(), timeout=MCP_INIT_TIMEOUT)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"MCP server '{server_path.name}' did not respond within {MCP_INIT_TIMEOUT}s. "
                "Check that the server script starts correctly."
            )

        log.info("[CHECKPOINT: MCP_SESSION_INIT] %s ready", server_path.name)

    async def _disconnect(self) -> None:
        if self._session_context:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception as exc:
                log.warning("[CHECKPOINT: MCP_CLOSE_WARN] Error closing session: %s", exc)

        if self._stdio_context:
            try:
                await self._stdio_context.__aexit__(None, None, None)
            except Exception as exc:
                log.warning("[CHECKPOINT: MCP_CLOSE_WARN] Error closing transport: %s", exc)

        log.info("[CHECKPOINT: MCP_CLOSED] Session closed")

    async def list_tools(self) -> list[Tool]:
        if self.session is None:
            raise RuntimeError("MCPClient is not connected.")

        response = await self.session.list_tools()
        tools: list[Tool] = response.tools
        log.info("[CHECKPOINT: MCP_TOOLS_DISCOVERED] Exposes %d tool(s): %s", len(tools), [t.name for t in tools])
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if self.session is None:
            raise RuntimeError("MCPClient is not connected.")

        log.info("[CHECKPOINT: MCP_CALL_TOOL] Invoking '%s' with args: %s", tool_name, arguments)
        result = await self.session.call_tool(tool_name, arguments=arguments)

        if not result.content:
            raise ValueError(f"Tool '{tool_name}' returned an empty result.")

        text_parts: list[str] = [
            block.text for block in result.content if hasattr(block, "text")
        ]

        if not text_parts:
            raise ValueError(f"Tool '{tool_name}' returned no text content.")

        combined = "\n".join(text_parts)
        log.info("[CHECKPOINT: MCP_CALL_DONE] Tool '%s' returned %d chars", tool_name, len(combined))
        return combined
