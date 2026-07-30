# Architecture Overview

The **AI Teammate** project separates concerns strictly:

1. **FastAPI (`backend/app/api/`)**: HTTP ingress/egress. It performs input validation, responds to external webhooks immediately (important for Slack's 3-second limit), and offloads processing to the background.
2. **Orchestrator (`backend/app/orchestrator/`)**: The "Brain" controller. It routes user questions to Gemini, examines the response for tool-calls, and bridges the gap between LLMs and external systems.
3. **LLM Engine (`backend/app/llm/`)**: Communicates with the Google Gemini API.
4. **MCP Manager (`backend/app/mcp/`)**: Interacts with local or remote Model Context Protocol servers to dynamically supply tools.
5. **Tools Wrappers (`backend/app/tools/`)**: Code that standardizes interactions with the MCP client.

## Request Lifecycle
1. User @mentions bot in Slack.
2. Slack sends event payload to FastAPI.
3. FastAPI acknowledges and spawns an asynchronous task.
4. Orchestrator fetches available tools from MCP servers.
5. Orchestrator queries Gemini with tools context.
6. Gemini returns a `function_call`.
7. Orchestrator executes the tool via MCP client and sends result back.
8. Gemini generates final markdown output.
9. Orchestrator publishes result back to Slack.
