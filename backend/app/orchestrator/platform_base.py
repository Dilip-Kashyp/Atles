import abc
from typing import Any
from fastapi import Request, Response
from pydantic import BaseModel


class NormalizedEvent(BaseModel):
    channel: str
    thread_ts: str
    sender: str
    raw_text: str
    event_id: str
    workspace_id: str = ""


class ChatPlatform(abc.ABC):
    @abc.abstractmethod
    async def handle_request(self, request: Request, dispatch_func: Any) -> Response:
        pass

    @abc.abstractmethod
    async def send_typing_indicator(self, channel: str, thread_ts: str) -> None:
        pass

    @abc.abstractmethod
    async def send_reply(self, channel: str, thread_ts: str, text: str) -> None:
        pass
