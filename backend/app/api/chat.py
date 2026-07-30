import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_orchestrator
from app.orchestrator.agent import Orchestrator

log = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)


class ChatResponse(BaseModel):
    response: str
    tool_used: bool
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    log.info("[CHECKPOINT: CHAT_INGRESS] Received POST /chat request")
    result = await orchestrator.process(request.message)
    log.info("[CHECKPOINT: CHAT_EGRESS] Returning POST /chat response")

    return ChatResponse(
        response=result.response,
        tool_used=result.tool_used,
        tool_name=result.tool_name,
        tool_arguments=result.tool_arguments,
    )
