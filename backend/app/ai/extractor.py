from __future__ import annotations

import re

from app.ai.state import AtlasState


class Extractor:
    """Extracts simple structured information from free-form text."""

    def extract(self, state: AtlasState) -> AtlasState:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", state.input_text) if s.strip()]
        state.decisions = [s for s in sentences[:2]]
        state.questions = [s for s in sentences[-2:] if "?" in s]
        if not state.questions:
            state.questions = ["What would you like Atlas to do next?"]
        return state
