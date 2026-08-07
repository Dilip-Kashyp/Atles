from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.memory.models import Entity

log = logging.getLogger(__name__)

_EXTRACT_PROMPT = """You are a precise entity extractor for a developer-tools AI assistant.

STRICT OUTPUT CONTRACT — YOU MUST FOLLOW THESE RULES:
1. Return ONLY a valid JSON array. Nothing else.
2. No markdown fences (no ```json ... ```).
3. No explanation, no preamble, no trailing text.
4. Empty array [] if no entities found — do NOT return null or {{}}.
5. Every item MUST have exactly two keys: "type" and "value" (both strings).

Supported entity types → value format:
  repository   → "owner/repo"            e.g. "Dilip-Kashyp/bot"
  branch       → branch name             e.g. "main" or "feature/oauth"
  issue        → issue number (string)   e.g. "42"
  pr           → PR number (string)      e.g. "17"
  technology   → tech name               e.g. "Redis", "FastAPI", "MongoDB"
  user         → Slack handle or GitHub username  e.g. "rahul"
  channel      → Slack channel           e.g. "#general"
  jira_ticket  → Jira key                e.g. "PROJ-123"
  notion_page  → Page title              e.g. "FAANG Interview Prep"

Required output format (array of objects):
[{{"type": "repository", "value": "owner/repo"}}, ...]

Conversation text to extract from:
\"\"\"
{text}
\"\"\"
"""


class _RawEntity(BaseModel):
    type:  str = Field(default="")
    value: str = Field(default="")

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def _normalise_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if not data.get("type"):
            for alt in ("kind", "entity_type", "category", "label"):
                if data.get(alt):
                    data["type"] = data[alt]
                    break
        if not data.get("value"):
            for alt in ("name", "val", "content", "text"):
                if data.get(alt):
                    data["value"] = data[alt]
                    break
        return data

    def to_entity(self) -> Entity | None:
        if self.type and self.value:
            return Entity(type=self.type.strip(), value=str(self.value).strip())
        return None


class EntityExtractor:
    _MODEL = "gemini-2.0-flash"

    def __init__(self, gemini_api_key: str) -> None:
        self._api_key = gemini_api_key

    async def extract(self, text: str) -> list[Entity]:
        if not text or not text.strip():
            return []

        try:
            from google import genai

            client = genai.Client(api_key=self._api_key)
            prompt = _EXTRACT_PROMPT.format(text=text[:2000])

            response = await client.aio.models.generate_content(
                model=self._MODEL,
                contents=prompt,
            )
            raw = (response.text or "").strip()

            if not raw:
                log.debug("[EXTRACTOR] Empty response from model")
                return []

            if raw.startswith("```"):
                inner = raw.strip("`")
                inner = inner.removeprefix("json")
                raw = inner.strip()

            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError as je:
                log.warning(
                    "[EXTRACTOR] JSON parse failed: %s | raw=%r", je, raw[:300]
                )
                return []

            if isinstance(parsed, dict):
                for wrapper_key in ("entities", "results", "items", "data"):
                    if isinstance(parsed.get(wrapper_key), list):
                        parsed = parsed[wrapper_key]
                        break
                else:
                    log.debug(
                        "[EXTRACTOR] Got dict but no known wrapper key: %r",
                        list(parsed.keys()),
                    )
                    return []

            if not isinstance(parsed, list):
                log.debug("[EXTRACTOR] Expected list, got %s", type(parsed).__name__)
                return []

            entities: list[Entity] = []
            skipped = 0
            for item in parsed:
                if not isinstance(item, dict):
                    skipped += 1
                    continue
                try:
                    raw_entity = _RawEntity.model_validate(item)
                    entity = raw_entity.to_entity()
                    if entity:
                        entities.append(entity)
                    else:
                        log.debug("[EXTRACTOR] Item skipped (empty type/value): %r", item)
                        skipped += 1
                except Exception as item_exc:
                    log.debug(
                        "[EXTRACTOR] Item validation failed: %s | item=%r", item_exc, item
                    )
                    skipped += 1

            log.info(
                "[CHECKPOINT: EXTRACTOR_DONE] extracted=%d skipped=%d from %d chars",
                len(entities),
                skipped,
                len(text),
            )
            return entities

        except Exception as exc:
            log.warning(
                "[CHECKPOINT: EXTRACTOR_FALLBACK] Extraction failed: %s", exc
            )
            return []
