"""
Atlas Backend FastAPI Application Entry Point.
"""
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, dashboard, integrations, slack, webhooks
from app.api.v1 import v1_router
from app.config import get_settings
from app.errors import register_error_handlers
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
    log.info("[CHECKPOINT: APP_STARTUP] Starting Atlas platform")

    if not settings.gemini_api_key:
        log.critical("Missing core settings (GEMINI_API_KEY).")
        sys.exit(1)

    # Validate Gemini and Slack connection
    await run_preflight_checks(settings)

    log.info("[CHECKPOINT: APP_READY] Atlas backend ready")
    yield
    log.info("[CHECKPOINT: APP_SHUTDOWN] Cleanup finished")


app = FastAPI(
    title="Atlas API",
    description="Atlas Enterprise Conversation Intelligence Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
settings = get_settings()
allowed_origins = [settings.frontend_origin.rstrip("/")]
if "http://localhost:3000" not in allowed_origins:
    allowed_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

register_error_handlers(app)

# Include API v1 routes
app.include_router(v1_router, prefix="/api")

# Include legacy router endpoints for backward compatibility
app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(slack.router)
app.include_router(webhooks.router)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "atlas-platform"}


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "name": "Atlas Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "v1_api": "/api/v1",
    }
