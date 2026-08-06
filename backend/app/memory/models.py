from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    PREFERENCE             = "preference"
    WORKING_STATE_SNAPSHOT = "working_state_snapshot"
    DISCUSSION_SUMMARY     = "discussion_summary"
    TOOL_RESULT            = "tool_result"


class IntentClass(str, Enum):
    TRIVIAL = "trivial"
    GITHUB  = "github"
    NOTION  = "notion"
    JIRA    = "jira"
    SLACK   = "slack"
    GENERAL = "general"


class Entity(BaseModel):
    type: str
    value: str

    def __hash__(self) -> int:
        return hash((self.type, self.value))


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
    active_tool: str      = ""
    github: GitHubState   = Field(default_factory=GitHubState)
    jira: JiraState       = Field(default_factory=JiraState)
    notion: NotionState   = Field(default_factory=NotionState)
    extra: dict[str, Any] = Field(default_factory=dict)


class SessionContext(BaseModel):
    session_key: str
    workspace_id: str = ""
    user_id: str      = ""
    channel_id: str   = ""
    thread_ts: str    = ""
    working_state: WorkingState = Field(default_factory=WorkingState)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Memory(BaseModel):
    session_key: str
    memory_type: MemoryType
    summary: str
    entities: list[Entity]          = Field(default_factory=list)
    importance: float               = 0.5
    created_at: datetime            = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime            = Field(default_factory=lambda: datetime.now(timezone.utc))


class SlackThreadMeta(BaseModel):
    thread_ts: str
    channel_id: str
    workspace_id: str        = ""
    participants: list[str]  = Field(default_factory=list)
    message_count: int       = 0
    tags: list[str]          = Field(default_factory=list)
    updated_at: datetime     = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryContext(BaseModel):
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


class PromptContext(BaseModel):
    working_state: WorkingState          = Field(default_factory=WorkingState)
    memory_context: MemoryContext        = Field(default_factory=MemoryContext)
    slack_thread_meta: SlackThreadMeta | None = None
    intent: IntentClass                  = IntentClass.GENERAL
