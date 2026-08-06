from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AtlasState:
    """Structured state passed through the Atlas AI pipeline."""

    input_text: str
    summary: str | None = None
    decisions: list[str] = field(default_factory=list)
    action_items: list[dict[str, Any]] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    reply: str | None = None
    error: str | None = None
