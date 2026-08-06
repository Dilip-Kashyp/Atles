from __future__ import annotations

from app.ai.state import AtlasState


class Summarizer:
    """Produces a simple deterministic summary."""

    def summarize(self, state: AtlasState) -> AtlasState:
        text = state.input_text.strip()
        state.summary = text[:160] if len(text) > 160 else text
        return state
