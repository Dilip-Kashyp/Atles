from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from app.memory.cache import RuntimeCache
from app.memory.extractor import EntityExtractor
from app.memory.models import (
    Entity,
    GitHubState,
    IntentClass,
    JiraState,
    Memory,
    MemoryContext,
    MemoryType,
    NotionState,
    PromptContext,
    SessionContext,
    SlackThreadMeta,
    WorkingState,
)
from app.memory.prompt_context import PromptContextBuilder
from app.memory.repository import MemoryRepository

log = logging.getLogger(__name__)

_LIMIT_PREFERENCES  = 2
_LIMIT_TOOL_RESULTS = 1
_LIMIT_SUMMARIES    = 2
_LIMIT_ENTITIES     = 10

_TRIVIAL_RE = re.compile(
    r"^(hi+|hello+|hey+|sup|what'?s up|howdy|yo|"
    r"hi there|hello there|hey there|good morning|good afternoon|good evening|"
    r"thanks?|thank you|cheers|np|no prob|"
    r"ok(?:ay)?|sure|yes|no|yep|nope|got it|sounds good|will do|"
    r"good|great|nice|cool|awesome|perfect|noted|"
    r"[👍🙏✅👏🎉]+)[\s!?.]*$",
    re.IGNORECASE,
)
_GITHUB_RE = re.compile(
    r"\b(issue|issues|pr|pull.?request|branch|repo|repository|"
    r"github|commit|merge|fork|star|release|tag|clone)\b",
    re.IGNORECASE,
)
_NOTION_RE = re.compile(
    r"\b(notion|doc|document|page|database|wiki|find|search|lookup)\b",
    re.IGNORECASE,
)
_JIRA_RE = re.compile(
    r"\b(jira|ticket|sprint|story|epic|backlog|board|project)\b",
    re.IGNORECASE,
)
_SLACK_RE = re.compile(
    r"\b(slack|channel|message|thread|read|summarize|summary|dm|direct)\b",
    re.IGNORECASE,
)

_MIN_MEANINGFUL_LEN = 8

SlackReadFn = Callable[[str, str], Coroutine[Any, Any, str]]


def _classify_intent(user_message: str) -> IntentClass:
    stripped = user_message.strip()

    if len(stripped) < _MIN_MEANINGFUL_LEN or _TRIVIAL_RE.match(stripped):
        return IntentClass.TRIVIAL

    if _GITHUB_RE.search(stripped):
        return IntentClass.GITHUB
    if _NOTION_RE.search(stripped):
        return IntentClass.NOTION
    if _JIRA_RE.search(stripped):
        return IntentClass.JIRA
    if _SLACK_RE.search(stripped):
        return IntentClass.SLACK

    return IntentClass.GENERAL


def _is_worth_remembering(user_message: str, assistant_response: str) -> bool:
    user   = user_message.strip()
    bot    = assistant_response.strip()

    if len(user) < _MIN_MEANINGFUL_LEN and len(bot) < 50:
        return False

    if _TRIVIAL_RE.match(user):
        return False

    return True


class MemoryManager:
    def __init__(
        self,
        repository: MemoryRepository,
        cache: RuntimeCache,
        extractor: EntityExtractor,
        context_builder: PromptContextBuilder,
        slack_read_fn: SlackReadFn | None = None,
    ) -> None:
        self._repo       = repository
        self._cache      = cache
        self._extract    = extractor
        self._builder    = context_builder
        self._slack_read = slack_read_fn

    async def load_context(
        self,
        session_ctx: SessionContext,
        user_message: str = "",
    ) -> PromptContext:
        intent = _classify_intent(user_message)

        log.info(
            "[CHECKPOINT: MEMORY_LOAD_START] session=%s intent=%s",
            session_ctx.session_key,
            intent.value,
        )

        session = await self._resolve_session(session_ctx)
        ws = session.working_state

        preferences:  list[Memory] = []
        tool_results: list[Memory] = []
        summaries:    list[Memory] = []
        all_entities: list[Entity] = []

        if intent != IntentClass.TRIVIAL:
            preferences  = await self._safe_find_memories(
                session.session_key, MemoryType.PREFERENCE, _LIMIT_PREFERENCES
            )
            tool_results = await self._safe_find_memories(
                session.session_key, MemoryType.TOOL_RESULT, _LIMIT_TOOL_RESULTS
            )
            summaries    = await self._safe_find_memories(
                session.session_key, MemoryType.DISCUSSION_SUMMARY, _LIMIT_SUMMARIES
            )
            seen: set[tuple[str, str]] = set()
            for mem in [*preferences, *tool_results, *summaries]:
                for e in mem.entities:
                    key = (e.type, e.value)
                    if key not in seen:
                        seen.add(key)
                        all_entities.append(e)
                        if len(all_entities) >= _LIMIT_ENTITIES:
                            break

        if ws.active_tool and intent not in (IntentClass.TRIVIAL,):
            tool_type_map: dict[str, IntentClass] = {
                "github": IntentClass.GITHUB,
                "notion": IntentClass.NOTION,
                "jira":   IntentClass.JIRA,
                "slack":  IntentClass.SLACK,
            }
            active_intent = tool_type_map.get(ws.active_tool, IntentClass.GENERAL)
            if intent == IntentClass.GENERAL:
                intent = active_intent

        memory_context = MemoryContext(
            preferences=preferences,
            tool_results=tool_results,
            summaries=summaries,
            entities=all_entities,
        )

        slack_meta: SlackThreadMeta | None = None
        if session.thread_ts and session.channel_id:
            slack_meta = await self._safe_find_slack_thread(
                session.thread_ts, session.channel_id
            )

        ctx = PromptContext(
            working_state=ws,
            memory_context=memory_context,
            slack_thread_meta=slack_meta,
            intent=intent,
        )

        prefix = self._builder.build(ctx)

        ws_summary = (
            f"github.repo={ws.github.repo}" if ws.github.repo
            else f"active={ws.active_tool}" if ws.active_tool
            else "empty"
        )
        log.info(
            "[CHECKPOINT: MEMORY_LOAD_DONE] session=%s intent=%s | "
            "ws=(%s) | prefs=%d summaries=%d tool_results=%d entities=%d | "
            "prompt_prefix=%d chars",
            session.session_key,
            intent.value,
            ws_summary,
            len(preferences),
            len(summaries),
            len(tool_results),
            len(all_entities),
            len(prefix),
        )

        return ctx

    async def on_tool_success(
        self,
        session_key: str,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_result: str,
    ) -> None:
        log.info(
            "[CHECKPOINT: MEMORY_TOOL_UPDATE] session=%s tool=%s",
            session_key,
            tool_name,
        )

        session = await self._resolve_session_by_key(session_key)
        ws = session.working_state

        if tool_name == "open_issue":
            repo = tool_args.get("repo", "")
            if repo:
                ws.github = GitHubState(
                    repo=repo,
                    branch=ws.github.branch,
                    issue=_extract_issue_number(tool_result),
                    pr=ws.github.pr,
                )
                ws.active_tool = "github"

        elif tool_name in ("create_pr", "open_pr"):
            repo = tool_args.get("repo", "")
            if repo:
                ws.github = GitHubState(
                    repo=repo,
                    branch=tool_args.get("head_branch", ws.github.branch),
                    issue=ws.github.issue,
                    pr=_extract_pr_number(tool_result),
                )
                ws.active_tool = "github"

        elif tool_name == "read_messages":
            channel = tool_args.get("channel", "")
            if channel and session.thread_ts:
                asyncio.create_task(
                    self._safe_upsert_slack_thread(
                        SlackThreadMeta(
                            thread_ts=session.thread_ts,
                            channel_id=session.channel_id or channel,
                            workspace_id=session.workspace_id,
                        )
                    )
                )

        elif tool_name == "find_document":
            page_title = tool_args.get("query", "")
            ws.notion = NotionState(page=page_title)
            ws.active_tool = "notion"

        elif tool_name in ("jira_create_issue", "jira_assign_ticket"):
            project = tool_args.get("project", ws.jira.project)
            ticket  = _extract_jira_key(tool_result)
            ws.jira = JiraState(project=project, ticket=ticket or ws.jira.ticket)
            ws.active_tool = "jira"

        else:
            ws.extra[tool_name] = tool_args.get("repo") or tool_args.get("id") or ""

        session.working_state = ws
        await self._safe_upsert_session(session)

        asyncio.create_task(
            self._safe_save_memory(
                Memory(
                    session_key=session_key,
                    memory_type=MemoryType.TOOL_RESULT,
                    summary=(
                        f"Tool '{tool_name}' called with {tool_args}. "
                        f"Result: {tool_result[:300]}"
                    ),
                    importance=0.7,
                )
            )
        )

    async def persist_turn(
        self,
        session_key: str,
        user_message: str,
        assistant_response: str,
    ) -> None:
        if not _is_worth_remembering(user_message, assistant_response):
            log.debug(
                "[CHECKPOINT: MEMORY_TURN_SKIPPED] Trivial turn, skipping persistence"
            )
            return

        asyncio.create_task(
            self._async_persist_turn(session_key, user_message, assistant_response)
        )

    async def fetch_slack_thread(self, channel: str, thread_ts: str) -> str:
        if self._slack_read is None:
            log.warning("[CHECKPOINT: MEMORY_SLACK_FALLBACK_SKIP] No Slack read fn injected")
            return ""

        log.info(
            "[CHECKPOINT: MEMORY_SLACK_FALLBACK] channel=%s ts=%s", channel, thread_ts
        )
        try:
            return await self._slack_read(channel, thread_ts)
        except Exception as exc:
            log.warning("[CHECKPOINT: MEMORY_SLACK_FALLBACK_ERR] %s", exc)
            return ""

    async def _resolve_session(self, ctx: SessionContext) -> SessionContext:
        cached = self._cache.get_session(ctx.session_key)
        if cached is not None:
            cached.channel_id   = ctx.channel_id   or cached.channel_id
            cached.thread_ts    = ctx.thread_ts     or cached.thread_ts
            cached.workspace_id = ctx.workspace_id  or cached.workspace_id
            cached.user_id      = ctx.user_id       or cached.user_id
            return cached

        persisted = await self._safe_load_session(ctx.session_key)
        if persisted is not None:
            persisted.channel_id   = ctx.channel_id   or persisted.channel_id
            persisted.thread_ts    = ctx.thread_ts     or persisted.thread_ts
            persisted.workspace_id = ctx.workspace_id  or persisted.workspace_id
            persisted.user_id      = ctx.user_id       or persisted.user_id
            self._cache.set_session(persisted.session_key, persisted)
            return persisted

        self._cache.set_session(ctx.session_key, ctx)
        return ctx

    async def _resolve_session_by_key(self, session_key: str) -> SessionContext:
        cached = self._cache.get_session(session_key)
        if cached is not None:
            return cached
        persisted = await self._safe_load_session(session_key)
        if persisted is not None:
            self._cache.set_session(session_key, persisted)
            return persisted
        stub = SessionContext(session_key=session_key)
        self._cache.set_session(session_key, stub)
        return stub

    async def _async_persist_turn(
        self,
        session_key: str,
        user_message: str,
        assistant_response: str,
    ) -> None:
        combined  = f"User: {user_message}\nBot: {assistant_response}"
        entities  = await self._extract.extract(combined)

        if len(assistant_response) > 80:
            summary = assistant_response[:300]
        else:
            summary = f"{user_message[:120]} → {assistant_response[:150]}"

        importance = min(0.9, 0.4 + len(entities) * 0.1 + min(len(assistant_response) / 2000, 0.3))

        await self._safe_save_memory(
            Memory(
                session_key=session_key,
                memory_type=MemoryType.DISCUSSION_SUMMARY,
                summary=summary,
                entities=entities,
                importance=importance,
            )
        )
        log.info(
            "[CHECKPOINT: MEMORY_TURN_PERSISTED] session=%s entities=%d importance=%.2f",
            session_key,
            len(entities),
            importance,
        )

    async def _safe_load_session(self, session_key: str) -> SessionContext | None:
        try:
            return await self._repo.load_session(session_key)
        except Exception as exc:
            log.warning("[MEMORY_MANAGER] load_session failed: %s", exc)
            return None

    async def _safe_upsert_session(self, ctx: SessionContext) -> None:
        self._cache.set_session(ctx.session_key, ctx)
        try:
            await self._repo.upsert_session(ctx)
        except Exception as exc:
            log.warning("[MEMORY_MANAGER] upsert_session failed: %s", exc)

    async def _safe_save_memory(self, memory: Memory) -> None:
        try:
            await self._repo.save_memory(memory)
        except Exception as exc:
            log.warning("[MEMORY_MANAGER] save_memory failed: %s", exc)

    async def _safe_find_memories(
        self,
        session_key: str,
        memory_type: MemoryType,
        limit: int,
    ) -> list[Memory]:
        try:
            return await self._repo.find_memories(
                session_key, limit=limit, memory_type=memory_type.value
            )
        except Exception as exc:
            log.warning(
                "[MEMORY_MANAGER] find_memories failed type=%s: %s",
                memory_type.value,
                exc,
            )
            return []

    async def _safe_find_slack_thread(
        self, thread_ts: str, channel_id: str
    ) -> SlackThreadMeta | None:
        try:
            return await self._repo.find_slack_thread(thread_ts, channel_id)
        except Exception as exc:
            log.warning("[MEMORY_MANAGER] find_slack_thread failed: %s", exc)
            return None

    async def _safe_upsert_slack_thread(self, meta: SlackThreadMeta) -> None:
        try:
            await self._repo.upsert_slack_thread(meta)
        except Exception as exc:
            log.warning("[MEMORY_MANAGER] upsert_slack_thread failed: %s", exc)


def _extract_issue_number(tool_result: str) -> str:
    match = re.search(r'"number"\s*:\s*(\d+)', tool_result)
    return match.group(1) if match else ""


def _extract_pr_number(tool_result: str) -> str:
    match = re.search(r'"number"\s*:\s*(\d+)', tool_result)
    return match.group(1) if match else ""


def _extract_jira_key(tool_result: str) -> str:
    match = re.search(r'[A-Z][A-Z0-9]+-\d+', tool_result)
    return match.group(0) if match else ""
