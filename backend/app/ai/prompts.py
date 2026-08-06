from __future__ import annotations

from typing import Any


def build_prompts(text: str) -> dict[str, Any]:
    """Return a minimal prompt payload for the Atlas AI pipeline."""

    return {
        "user_input": text,
        "system_prompt": "You are Atlas, a helpful conversation intelligence assistant.",
        "summary_prompt": "Summarize the conversation concisely.",
        "action_prompt": "Identify the next action to take.",
    }
