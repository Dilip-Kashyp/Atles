"""
app/memory/models.py
────────────────────
All Pydantic domain models for the memory system.
No I/O. No external dependencies. Pure data structures.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class MemoryType(str, Enum):
    PREFERENCE             = "preference"
    WORKING_STATE_SNAPSHOT = "working_state_snapshot"
    DISCUSSION_SUMMARY     = "discussion_summary"
    TOOL_RESULT            = "tool_result"


class IntentClass(str, Enum):
    """
    Lightweight intent classification for a user message.
    Determined by regex — zero LLM cost.
    Used to decide which memory categories to retrieve and inject.
    """
    TRIVIAL = "trivial"   # greetings, ack, single-word replies
    GITHUB  = "github"    # issue, PR, branch, repo, commit
    NOTION  = "notion"    # doc, page, find, database, search
    JIRA    = "jira"      # ticket, sprint, story, epic
    SLACK   = "slack"     # channel, message, thread, read
    GENERAL = "general"   # anything not matched above


# ── Entity ─────────────────────────────────────────────────────────────────────

class Entity(BaseModel):
    """A structured entity extracted from a conversation turn."""
    type: str   # e.g. "repository", "branch", "issue", "technology", "user"
    value: str  # e.g. "Dilip-Kashyp/bot", "main", "42", "Redis"

    def __hash__(self) -> int:
        return hash((self.type, self.value))


# ── Working State ──────────────────────────────────────────────────────────────

class GitHubState(BaseModel):
    repo: str   = ""
    branch: str = ""
    issue: str  = ""
    pr: str     = ""

class JiraState(BaseModel):
    project: str = ""
    ticket: str  = ""

class NotionState(BaseModel):
    page: str     = ""
    database: str = ""


class WorkingState(BaseModel):
    """
    The currently active tool context for a session.
    Updated immediately after every successful MCP tool call.
    """
    active_tool: str      = ""
    github: GitHubState   = Field(default_factory=GitHubState)
    jira: JiraState       = Field(default_factory=JiraState)
    notion: NotionState   = Field(default_factory=NotionState)
    # Extensible: add new tool namespaces here without touching MemoryManager core
    extra: dict[str, Any] = Field(default_factory=dict)


# ── Session ────────────────────────────────────────────────────────────────────

class SessionContext(BaseModel):
    """
    Identifies and carries the runtime state for one conversation session.
    Built by the API layer (api/slack.py or api/chat.py) from the platform event.
    Passed into Orchestrator.process() as an optional argument.
    """
    session_key: str         # Primary identifier — see session key strategy
    workspace_id: str = ""   # Slack team_id or equivalent
    user_id: str      = ""   # Slack user id of the person who sent the message
    channel_id: str   = ""
    thread_ts: str    = ""
    working_state: WorkingState = Field(default_factory=WorkingState)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Memory (durable knowledge document) ───────────────────────────────────────

class Memory(BaseModel):
    """A single durable knowledge document persisted in MongoDB memories collection."""
    session_key: str
    memory_type: MemoryType
    summary: str                    # Natural language summary
    entities: list[Entity]          = Field(default_factory=list)
    importance: float               = 0.5   # 0.0 – 1.0; higher = surfaced first
    created_at: datetime            = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime            = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Slack Thread Metadata ──────────────────────────────────────────────────────

class SlackThreadMeta(BaseModel):
    """Slim metadata about a Slack thread. NO message content stored here."""
    thread_ts: str
    channel_id: str
    workspace_id: str        = ""
    participants: list[str]  = Field(default_factory=list)
    message_count: int       = 0
    tags: list[str]          = Field(default_factory=list)
    updated_at: datetime     = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Memory Context (structured, per-category retrieval result) ─────────────────

class MemoryContext(BaseModel):
    """
    Structured memory retrieval result — replaces the flat list[Memory].
    Each category is fetched independently and rendered differently in the prompt.

    Why categorised:
      • Preferences  → always useful regardless of intent
      • ToolResults  → most recent action — critical for follow-ups
      • Summaries    → only when intent is non-trivial
      • Entities     → deduplicated, used for cross-referencing
    """
    preferences:  list[Memory] = Field(default_factory=list)
    tool_results: list[Memory] = Field(default_factory=list)
    summaries:    list[Memory] = Field(default_factory=list)
    entities:     list[Entity] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return (
            not self.preferences
            and not self.tool_results
            and not self.summaries
            and not self.entities
        )


# ── Prompt Context (compiled, ready to render) ─────────────────────────────────

class PromptContext(BaseModel):
    """
    The compiled context object produced by MemoryManager.load_context().
    Consumed by PromptContextBuilder to produce a compact prefix string for Gemini.

    Change from v1: `recent_memories: list[Memory]` replaced by structured
    `memory_context: MemoryContext` — enables type-aware prompt rendering.
    """
    working_state: WorkingState          = Field(default_factory=WorkingState)
    memory_context: MemoryContext        = Field(default_factory=MemoryContext)
    slack_thread_meta: SlackThreadMeta | None = None
    intent: IntentClass                  = IntentClass.GENERAL
