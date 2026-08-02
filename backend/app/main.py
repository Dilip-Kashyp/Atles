import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slack_sdk import WebClient

from app.api import chat, slack
from app.config import get_settings
from app.errors import register_error_handlers
from app.llm.gemini import GeminiClient
from app.mcp.client import MCPClient
from app.orchestrator.agent import Orchestrator
from app.orchestrator.slack_handler import SlackPlatform
from app.orchestrator.tool_dispatcher import ToolDispatcher
from app.startup_checks import run_preflight_checks

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    log.info("[CHECKPOINT: APP_STARTUP] Starting AI Teammate")

    if not settings.slack_bot_token or not settings.gemini_api_key:
        log.critical("Missing core secrets (SLACK_BOT_TOKEN or GEMINI_API_KEY).")
        sys.exit(1)

    await run_preflight_checks(settings)

    slack_client = WebClient(token=settings.slack_bot_token)
    slack_platform = SlackPlatform(settings=settings, client=slack_client)
    await slack_platform.validate_startup()
    app.state.slack_platform = slack_platform

    dispatcher = ToolDispatcher()

    slack_mcp = MCPClient(
        server_script=settings.mcp_server_script,
        extra_env={"SLACK_BOT_TOKEN": settings.slack_bot_token},
    )
    await slack_mcp.__aenter__()
    await dispatcher.register_mcp_client_tools(slack_mcp)
    app.state.slack_mcp = slack_mcp

    if settings.github_token:
        try:
            github_mcp = MCPClient(
                server_script=settings.github_mcp_server_script,
                extra_env={"GITHUB_TOKEN": settings.github_token},
            )
            await github_mcp.__aenter__()
            await dispatcher.register_mcp_client_tools(github_mcp)
            app.state.github_mcp = github_mcp
        except Exception as exc:
            log.error("[CHECKPOINT: MCP_SKIP] GitHub MCP failed to start: %s", exc)
            app.state.github_mcp = None
    else:
        app.state.github_mcp = None

    if settings.notion_token:
        try:
            notion_mcp = MCPClient(
                server_script=settings.notion_mcp_server_script,
                extra_env={"NOTION_TOKEN": settings.notion_token},
            )
            await notion_mcp.__aenter__()
            await dispatcher.register_mcp_client_tools(notion_mcp)
            app.state.notion_mcp = notion_mcp
        except Exception as exc:
            log.error("[CHECKPOINT: MCP_SKIP] Notion MCP failed to start: %s", exc)
            app.state.notion_mcp = None
    else:
        app.state.notion_mcp = None

    app.state.dispatcher = dispatcher

    llm = GeminiClient(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
        tools=dispatcher.get_all_tools(),
    )
    app.state.llm_client = llm

    # ── Memory System (optional — feature-flagged) ─────────────────────────────
    memory_manager = None
    if settings.mongodb_uri and settings.memory_enabled:
        try:
            from app.memory.cache import RuntimeCache
            from app.memory.extractor import EntityExtractor
            from app.memory.manager import MemoryManager
            from app.memory.prompt_context import PromptContextBuilder
            from app.memory.repository import MemoryRepository

            repo = MemoryRepository(
                mongo_uri=settings.mongodb_uri,
                db_name=settings.mongodb_db_name,
            )
            await repo.ensure_indexes()

            cache = RuntimeCache(
                max_size=settings.memory_cache_max_size,
                ttl_seconds=settings.memory_cache_ttl_seconds,
            )
            extractor = EntityExtractor(gemini_api_key=settings.gemini_api_key)
            builder   = PromptContextBuilder()

            # Inject the Slack MCP read_messages callable as the cold-storage fallback
            async def _slack_read(channel: str, thread_ts: str) -> str:
                return await slack_mcp.call_tool(
                    "read_messages", {"channel": channel, "thread_ts": thread_ts}
                )

            memory_manager = MemoryManager(
                repository=repo,
                cache=cache,
                extractor=extractor,
                context_builder=builder,
                slack_read_fn=_slack_read,
            )
            app.state.memory_repo = repo
            log.info("[CHECKPOINT: MEMORY_READY] Memory system initialized (MongoDB)")
        except Exception as exc:
            log.error("[CHECKPOINT: MEMORY_SKIP] Memory system failed to initialize: %s", exc)
            memory_manager = None
    else:
        log.warning(
            "[CHECKPOINT: MEMORY_DISABLED] MONGODB_URI not set or MEMORY_ENABLED=false. "
            "Running in stateless mode."
        )

    app.state.memory_manager = memory_manager

    orchestrator = Orchestrator(
        llm_client=llm,
        tool_dispatcher=dispatcher,
        memory_manager=memory_manager,
    )
    app.state.orchestrator = orchestrator

    log.info("[CHECKPOINT: APP_READY] All services & MCP servers registered")
    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    for mcp_attr in ("slack_mcp", "github_mcp", "notion_mcp"):
        mcp_instance = getattr(app.state, mcp_attr, None)
        if mcp_instance is not None:
            await mcp_instance.__aexit__(None, None, None)

    if memory_manager is not None:
        repo_instance = getattr(app.state, "memory_repo", None)
        if repo_instance is not None:
            await repo_instance.disconnect()

    log.info("[CHECKPOINT: APP_SHUTDOWN] Cleanup finished")



app = FastAPI(
    title="AI Teammate",
    description="Production AI Teammate API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(chat.router)
app.include_router(slack.router)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-teammate"}


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "name": "AI Teammate",
        "version": "1.0.0",
        "docs": "/docs",
        "chat_endpoint": "POST /chat/",
    }
