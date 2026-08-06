from __future__ import annotations

from app.memory.models import IntentClass, PromptContext

_SUMMARY_SUPPRESSED_INTENTS = frozenset({IntentClass.TRIVIAL})


class PromptContextBuilder:
    def build(self, ctx: PromptContext) -> str:
        sections: list[str] = []

        ws = ctx.working_state
        mc = ctx.memory_context

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

        for key, val in ws.extra.items():
            if val:
                ws_parts.append(f"{key}={val}")

        if ws_parts:
            sections.append("Working State: " + ", ".join(ws_parts))

        if mc.preferences:
            pref_lines = [f"  • {p.summary}" for p in mc.preferences]
            sections.append("User Preferences:\n" + "\n".join(pref_lines))

        if mc.tool_results:
            last = mc.tool_results[0]
            sections.append(f"Last Action: {last.summary[:200]}")

        if mc.summaries and ctx.intent not in _SUMMARY_SUPPRESSED_INTENTS:
            sum_lines = [f"  • {s.summary[:180]}" for s in mc.summaries]
            sections.append("Past Context:\n" + "\n".join(sum_lines))

        if mc.entities and ctx.intent not in _SUMMARY_SUPPRESSED_INTENTS:
            entity_parts = [f"{e.type}={e.value}" for e in mc.entities[:8]]
            sections.append("Known Entities: " + ", ".join(entity_parts))

        if not sections:
            return ""

        return (
            "[MEMORY CONTEXT]\n"
            + "\n".join(sections)
            + "\n[END MEMORY CONTEXT]\n\n"
        )
