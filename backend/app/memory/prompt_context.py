"""
app/memory/prompt_context.py
────────────────────────────
Builds a compact, structured context prefix for Gemini.

# FIX (Issues 2, 4, 5, 9):
# v1 received a flat `list[Memory]` and rendered everything blindly.
# v2 receives a structured `MemoryContext` with four independent categories:
#
#   • preferences  → rendered always (user config never hurts)
#   • tool_results → rendered as "Last action:" — critical for follow-ups
#   • summaries    → only rendered when intent is non-trivial
#   • entities     → compact key entities from past extractions
#
# Each category has its own rendering logic, so the prompt is meaningful,
# not just a flat bullet list of mixed types.
#
# The builder never renders empty sections — if all categories are empty
# (new session, trivial message) the return value is "" and the Orchestrator
# skips prepending entirely, making the prompt identical to pre-memory behaviour.

Design goals:
  • Provider-neutral — no Gemini imports
  • Compact — renders only non-empty sections
  • Deterministic — same MemoryContext always produces the same output
  • Intent-aware — summaries suppressed for trivial intents
"""
from __future__ import annotations

from app.memory.models import IntentClass, PromptContext

# Intents for which discussion summaries are NOT injected
_SUMMARY_SUPPRESSED_INTENTS = frozenset({IntentClass.TRIVIAL})


class PromptContextBuilder:
    """
    Converts a PromptContext into a compact text prefix.
    Returns empty string when there is nothing meaningful to add.
    """

    def build(self, ctx: PromptContext) -> str:
        sections: list[str] = []

        ws = ctx.working_state
        mc = ctx.memory_context

        # ── 1. Working State ───────────────────────────────────────────────────
        # Always include — this is the most critical context for follow-up actions.
        ws_parts: list[str] = []

        if ws.active_tool:
            ws_parts.append(f"active_tool={ws.active_tool}")

        gh = ws.github
        if gh.repo:
            ws_parts.append(f"github.repo={gh.repo}")
        if gh.branch:
            ws_parts.append(f"github.branch={gh.branch}")
        if gh.issue:
            ws_parts.append(f"github.issue=#{gh.issue}")
        if gh.pr:
            ws_parts.append(f"github.pr=#{gh.pr}")

        jira = ws.jira
        if jira.project:
            ws_parts.append(f"jira.project={jira.project}")
        if jira.ticket:
            ws_parts.append(f"jira.ticket={jira.ticket}")

        notion = ws.notion
        if notion.page:
            ws_parts.append(f"notion.page={notion.page}")

        # Future MCP servers via extra dict
        for key, val in ws.extra.items():
            if val:
                ws_parts.append(f"{key}={val}")

        if ws_parts:
            sections.append("Working State: " + ", ".join(ws_parts))

        # ── 2. User Preferences ────────────────────────────────────────────────
        # Render always — preferences are short, universally useful config.
        if mc.preferences:
            pref_lines = [f"  • {p.summary}" for p in mc.preferences]
            sections.append("User Preferences:\n" + "\n".join(pref_lines))

        # ── 3. Last Tool Action ────────────────────────────────────────────────
        # Most recent tool result — essential for "do it again" type follow-ups.
        if mc.tool_results:
            last = mc.tool_results[0]
            sections.append(f"Last Action: {last.summary[:200]}")

        # ── 4. Discussion Summaries ────────────────────────────────────────────
        # Suppressed for trivial intents (greetings, acks) to keep prompt lean.
        if mc.summaries and ctx.intent not in _SUMMARY_SUPPRESSED_INTENTS:
            sum_lines = [f"  • {s.summary[:180]}" for s in mc.summaries]
            sections.append("Past Context:\n" + "\n".join(sum_lines))

        # ── 5. Entities ────────────────────────────────────────────────────────
        # Compact — only shown if there are meaningful entities and intent warrants it.
        if mc.entities and ctx.intent not in _SUMMARY_SUPPRESSED_INTENTS:
            entity_parts = [f"{e.type}={e.value}" for e in mc.entities[:8]]
            sections.append("Known Entities: " + ", ".join(entity_parts))

        # ── Assemble ───────────────────────────────────────────────────────────
        if not sections:
            return ""

        return (
            "[MEMORY CONTEXT]\n"
            + "\n".join(sections)
            + "\n[END MEMORY CONTEXT]\n\n"
        )
