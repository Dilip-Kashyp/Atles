from __future__ import annotations

from app.ai.state import AtlasState


class Formatter:
    """Formats the final response for downstream channels."""

    def format(self, state: AtlasState) -> AtlasState:
        if state.tool_name:
            state.reply = f"Planned action: {state.tool_name}"
        else:
            state.reply = "No action planned."
        return state
