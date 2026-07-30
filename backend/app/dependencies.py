from fastapi import Request

from app.config import Settings, get_settings
from app.llm.base import LLMClient
from app.orchestrator.agent import Orchestrator
from app.orchestrator.platform_base import ChatPlatform
from app.orchestrator.tool_dispatcher import ToolDispatcher


def get_app_settings() -> Settings:
    return get_settings()


def get_slack_platform(request: Request) -> ChatPlatform:
    return request.app.state.slack_platform


def get_tool_dispatcher(request: Request) -> ToolDispatcher:
    return request.app.state.dispatcher


def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator
