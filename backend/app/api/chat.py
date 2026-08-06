import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.dependencies import get_orchestrator
from app.orchestrator.agent import Orchestrator

log = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    session_key: str | None = Field(
        default=None,
        description="Optional session key for memory continuity. Omit for a stateless request.",
    )


class ChatResponse(BaseModel):
    response: str
    tool_used: bool
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    session_key: str | None = None


@router.post("/", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    log.info("[CHECKPOINT: CHAT_INGRESS] Received POST /chat request")

    session_context = None
    memory_manager = getattr(request.app.state, "memory_manager", None)
    resolved_session_key: str | None = None

    if memory_manager is not None:
        from app.memory.models import SessionContext

        resolved_session_key = body.session_key or f"chat:{uuid.uuid4()}"
        session_context = SessionContext(session_key=resolved_session_key)
        log.info("[CHECKPOINT: CHAT_SESSION_BUILT] session_key=%s", resolved_session_key)

    result = await orchestrator.process(body.message, session_context=session_context)
    log.info("[CHECKPOINT: CHAT_EGRESS] Returning POST /chat response")

    return ChatResponse(
        response=result.response,
        tool_used=result.tool_used,
        tool_name=result.tool_name,
        tool_arguments=result.tool_arguments,
        session_key=resolved_session_key,
    )
