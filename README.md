# AI Teammate — Production Agentic Workflow Platform (Slack + FastAPI + Gemini + MCP)

A **production-grade, decoupled AI Teammate platform** designed with strict separation of concerns, clean architecture, dependency injection, and Model Context Protocol (MCP) integrations.

---

## Architecture Overview & Design Patterns

The system separates concerns across 4 key decoupled layers:

1. **Ingress & Platform Layer (`app/orchestrator/platform_base.py`, `app/orchestrator/slack_handler.py`)**:
   - Implements the `ChatPlatform` protocol.
   - Handles signature verification (HMAC-SHA256), event deduplication, URL verification handshakes, and event normalization into `NormalizedEvent`.
   - Extensible for future chat platforms (e.g. Microsoft Teams) without modifying core business logic.

2. **Orchestration Layer (`app/orchestrator/agent.py`)**:
   - `Orchestrator` class executing a 4-stage processing lifecycle.
   - Controls reasoning flow between the LLM client and the Tool Dispatcher.
   - Emits structured `[CHECKPOINT]` log telemetry at each stage.

3. **Tool Dispatcher & MCP Subprocess Layer (`app/orchestrator/tool_dispatcher.py`, `app/mcp/client.py`)**:
   - Manages multiple concurrent MCP server subprocesses (Slack, GitHub, Notion) via stdio transport.
   - Maps tool declarations dynamically into unified `MCPToolProxy` objects.
   - Implements strict tool boundaries.

4. **LLM Provider Layer (`app/llm/base.py`, `app/llm/gemini.py`)**:
   - Implements `LLMClient` protocol for provider neutrality (Gemini, Claude, etc.).
   - Converts MCP tools into native function declarations and handles tool response loops.

---

## Directory Structure

```
SlackBot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── chat.py           # REST Endpoint (POST /chat/)
│   │   │   └── slack.py          # Slack Webhook Endpoint (POST /slack/events)
│   │   ├── llm/
│   │   │   ├── base.py           # LLMClient Protocol
│   │   │   ├── gemini.py         # Google Gemini Implementation
│   │   │   └── prompts.py        # System Prompt & Parameter Rulebook
│   │   ├── mcp/
│   │   │   └── client.py         # Generic Stdio MCP Client Manager
│   │   ├── orchestrator/
│   │   │   ├── agent.py          # Core Orchestrator Class
│   │   │   ├── platform_base.py  # ChatPlatform Protocol & NormalizedEvent
│   │   │   ├── slack_handler.py  # SlackPlatform Implementation
│   │   │   └── tool_dispatcher.py# Tool Registry & Dispatcher
│   │   ├── tools/
│   │   │   ├── base.py           # BaseTool Protocol
│   │   │   ├── github.py         # GitHub Tool Scaffolding
│   │   │   ├── notion.py         # Notion Tool Scaffolding
│   │   │   └── slack.py          # MCPToolProxy Wrapper
│   │   ├── config.py             # Pydantic Settings (.env loader)
│   │   ├── dependencies.py       # FastAPI Depends() Providers
│   │   ├── errors.py             # Centralized Global Exception Handlers
│   │   └── main.py               # FastAPI App Lifespan & Initialization
│   ├── Dockerfile                # Backend Docker build script
│   ├── requirements.txt          # Python dependencies
│   └── vercel.json               # Serverless config
├── mcp-servers/
│   ├── slack/
│   │   ├── server.py             # FastMCP Slack Server (read_messages)
│   │   └── Dockerfile
│   ├── github/
│   │   ├── server.py             # FastMCP GitHub Server (open_issue)
│   │   ├── tools.py              # PyGithub Integration
│   │   └── Dockerfile
│   ├── notion/
│   │   ├── server.py             # FastMCP Notion Server (find_document)
│   │   ├── tools.py              # notion-client Integration
│   │   └── Dockerfile
│   └── jira/
│       └── tools.py              # Jira integration stub
├── docs/
│   ├── architecture.md           # Deep dive architecture docs
│   ├── deployment.md           # Docker & Serverless deployment guide
│   └── mcp.md                  # MCP integration guide
├── tests/                        # Unit test suite
├── .env.example                  # Environment template
├── docker-compose.yml            # Multi-container orchestration
└── README.md
```

---

## Execution Flow & Checkpoints

When a request is received (via Slack @mention or `POST /chat/`), it follows a strict checkpointed lifecycle:

```mermaid
sequenceDiagram
    actor User
    participant Ingress as API Router (chat/slack)
    participant Platform as SlackPlatform
    participant Orchestrator as Orchestrator
    participant LLM as GeminiClient
    participant Dispatcher as ToolDispatcher
    participant MCP as MCP Server Subprocess

    User->>Ingress: POST /slack/events or /chat/
    Ingress->>Platform: [CHECKPOINT: SLACK_INGRESS] Verify Signature & Parse
    Platform-->>Ingress: [CHECKPOINT: SLACK_AUTH_PASS] Verified
    Ingress->>Orchestrator: [CHECKPOINT 1/4: ORCHESTRATOR_START] Process query
    Orchestrator->>LLM: [CHECKPOINT 2/4: LLM_QUERY] Prompt model with tools
    LLM-->>Orchestrator: Request tool execution (e.g. open_issue)
    Orchestrator->>Dispatcher: [CHECKPOINT 3/4: TOOL_DISPATCH] Execute tool
    Dispatcher->>MCP: Forward via stdio RPC
    MCP-->>Dispatcher: Return result string/JSON
    Dispatcher-->>Orchestrator: Return result
    Orchestrator->>LLM: [CHECKPOINT: LLM_FEED_TOOL_RESULT] Feed tool output back
    LLM-->>Orchestrator: Generate final natural language answer
    Orchestrator-->>Ingress: [CHECKPOINT 4/4: ORCHESTRATOR_COMPLETE]
    Ingress->>Platform: [CHECKPOINT: SLACK_EGRESS] Reply to thread
```

---

## Quickstart

### 1. Environment Setup
Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env
```
Fill out the required secrets:
```env
GEMINI_API_KEY=your_gemini_api_key
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your_signing_secret

# Optional Integrations
GITHUB_TOKEN=ghp_your_github_token
NOTION_TOKEN=secret_your_notion_token
```

### 2. Run Backend
```bash
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
The server will automatically discover and launch all configured MCP servers (`slack`, `github`, `notion`) on startup.
