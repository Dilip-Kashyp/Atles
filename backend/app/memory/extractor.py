"""
app/memory/extractor.py
───────────────────────
Extracts structured entities from a conversation turn using a small,
fast Gemini call.

# ROOT CAUSE OF EXTRACTOR_FALLBACK (now fixed):
#   extract() is an `async` method but was calling the *synchronous*
#   client.models.generate_content() — blocking the event loop and causing
#   the SDK's internal response deserialization to raise KeyError: 'type'.
#
#   FIX: replaced with `await client.aio.models.generate_content(...)`,
#   the async variant of the same API.
#
# Additional hardening:
#   • _RawEntity Pydantic model accepts aliased key names (kind/entity_type/…)
#   • Per-item validation in try/except — one bad item never aborts the batch
#   • Unwraps {"entities": [...]} wrapper that some models return
#   • Logs raw response on parse failure for debuggability
#   • Never raises — empty list on any failure path
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.memory.models import Entity

log = logging.getLogger(__name__)

# ── Extraction Prompt ──────────────────────────────────────────────────────────
# RULES-AS-CODE: enforces strict JSON-only output at the prompt level.
_EXTRACT_PROMPT = """You are a precise entity extractor for a developer-tools AI assistant.

STRICT OUTPUT CONTRACT — YOU MUST FOLLOW THESE RULES:
1. Return ONLY a valid JSON array. Nothing else.
2. No markdown fences (no ```json ... ```).
3. No explanation, no preamble, no trailing text.
4. Empty array [] if no entities found — do NOT return null or {}.
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


# ── Schema Validation Model ────────────────────────────────────────────────────

class _RawEntity(BaseModel):
    """
    Tolerant Pydantic model for a single LLM-returned entity.

    LLMs occasionally return different key names ("kind" instead of "type",
    "name" instead of "value") or omit fields entirely. This model accepts
    all observed variants and normalises them to (type, value).

    Validation contract:
      • Both `type` and `value` must be non-empty strings after normalisation.
      • If either is empty, model_validate raises ValidationError and the
        item is skipped — the batch continues.
    """
    type:  str = Field(default="")
    value: str = Field(default="")

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def _normalise_keys(cls, data: Any) -> Any:
        """Remap alternative key names to canonical (type, value)."""
        if not isinstance(data, dict):
            return data
        # Type field aliases — some models use these instead of "type"
        if not data.get("type"):
            for alt in ("kind", "entity_type", "category", "label"):
                if data.get(alt):
                    data["type"] = data[alt]
                    break
        # Value field aliases
        if not data.get("value"):
            for alt in ("name", "val", "content", "text"):
                if data.get(alt):
                    data["value"] = data[alt]
                    break
        return data

    def to_entity(self) -> Entity | None:
        """Convert to domain Entity if both fields are non-empty."""
        if self.type and self.value:
            return Entity(type=self.type.strip(), value=str(self.value).strip())
        return None


# ── Extractor ──────────────────────────────────────────────────────────────────

class EntityExtractor:
    """
    Calls Gemini asynchronously to extract structured entities from text.
    Always returns a list — empty list on failure, never raises.

    IMPORTANT: extract() is async and uses client.aio (the async SDK surface).
    Do NOT switch back to client.models — that is synchronous and will block
    the FastAPI event loop.
    """

    _MODEL = "gemini-2.0-flash"

    def __init__(self, gemini_api_key: str) -> None:
        self._api_key = gemini_api_key

    async def extract(self, text: str) -> list[Entity]:
        """
        Extract entities from the given text.

        Uses await client.aio.models.generate_content() — the async SDK path.
        Each item is validated independently — one bad item skips, batch continues.
        """
        if not text or not text.strip():
            return []

        try:
            from google import genai  # lazy import

            client = genai.Client(api_key=self._api_key)
            prompt = _EXTRACT_PROMPT.format(text=text[:2000])  # cap input size

            # ── ASYNC call — this is the critical fix ──────────────────────────
            response = await client.aio.models.generate_content(
                model=self._MODEL,
                contents=prompt,
            )
            raw = (response.text or "").strip()

            if not raw:
                log.debug("[EXTRACTOR] Empty response from model")
                return []

            # ── Strip markdown fences (defensive — prompt forbids them) ────────
            if raw.startswith("```"):
                # e.g. ```json\n[...]\n``` → extract inner content
                inner = raw.strip("`")
                if inner.startswith("json"):
                    inner = inner[4:]
                raw = inner.strip()

            # ── Parse JSON ─────────────────────────────────────────────────────
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError as je:
                log.warning(
                    "[EXTRACTOR] JSON parse failed: %s | raw=%r", je, raw[:300]
                )
                return []

            # ── Unwrap {"entities": [...]} wrapper ─────────────────────────────
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

            # ── Validate each item independently ───────────────────────────────
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
            # Never block the main flow — extraction is best-effort
            log.warning(
                "[CHECKPOINT: EXTRACTOR_FALLBACK] Extraction failed: %s", exc
            )
            return []
