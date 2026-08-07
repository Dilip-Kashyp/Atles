from __future__ import annotations

from collections.abc import Awaitable, Callable


class ToolRegistry:
    """Simple in-process registry for workflow actions."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Awaitable[str] | str]] = {}

    def register(self, name: str, handler: Callable[..., Awaitable[str] | str]) -> None:
        self._handlers[name] = handler

    def get(self, name: str) -> Callable[..., Awaitable[str] | str] | None:
        return self._handlers.get(name)

    def as_dict(self) -> dict[str, Callable[..., Awaitable[str] | str]]:
        return dict(self._handlers)
