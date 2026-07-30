# Model Context Protocol (MCP)

This project heavily leverages the **Model Context Protocol** to decouple AI tool logic from the core orchestrator.

## How it works

Instead of hardcoding Slack API calls into the FastAPI backend, the backend simply asks the local "Slack MCP Server" (running in `mcp-servers/slack/server.py`) what tools it has.

The MCP Server responds with tools like `read_messages` and its JSON Schema. The FastAPI backend blindly forwards this schema to Gemini.

When Gemini wants to call `read_messages`, the FastAPI backend blindly forwards the call to the Slack MCP Server, which executes the real Python code to query Slack, and returns the result.

## Adding new servers

To add a GitHub integration:
1. Create `mcp-servers/github/server.py` and define tools for fetching PRs or Issues.
2. Ensure the orchestrator is configured to connect to it (via stdio or SSE).
3. The LLM instantly gains the ability to interact with GitHub without touching the core `agent.py` logic.
