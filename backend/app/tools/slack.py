import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.tools.base import BaseTool

log = logging.getLogger(__name__)


class SlackReadMessagesTool(BaseTool):
    """Reads recent messages from a Slack channel."""

    def __init__(self, client: WebClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "read_messages"

    @property
    def description(self) -> str:
        return (
            "Reads recent messages from a Slack channel or thread. "
            "Channel can be a name (e.g. 'general') or an ID (e.g. 'C12345')."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Slack channel name (e.g. 'general') or ID (e.g. 'C12345')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of messages to retrieve (1–100, default 20)",
                    "default": 20,
                },
            },
            "required": ["channel"],
        }

    async def execute(self, arguments: dict[str, Any]) -> str:
        channel = arguments["channel"]
        limit   = max(1, min(int(arguments.get("limit", 20)), 100))

        log.info("[CHECKPOINT: SLACK_READ_START] Reading %d messages from '%s'", limit, channel)

        try:
            result = await asyncio.to_thread(self._fetch_messages, channel, limit)
            log.info("[CHECKPOINT: SLACK_READ_DONE] '%s' — %s messages returned", channel, limit)
            return result
        except ValueError as exc:
            log.error("[CHECKPOINT: SLACK_READ_ERROR] %s", exc)
            return json.dumps({"error": str(exc)})
        except SlackApiError as exc:
            log.error("[CHECKPOINT: SLACK_READ_ERROR] Slack API: %s", exc.response["error"])
            return json.dumps({"error": f"Slack API error: {exc.response['error']}"})
        except Exception as exc:
            log.exception("[CHECKPOINT: SLACK_READ_ERROR] Unexpected error")
            return json.dumps({"error": f"Unexpected error: {exc}"})

    def _fetch_messages(self, channel: str, limit: int) -> str:
        channel_id = self._resolve_channel_id(channel)

        response = self._client.conversations_history(
            channel=channel_id,
            limit=limit,
        )
        messages = response.get("messages", [])

        if not messages:
            return json.dumps({
                "channel": channel,
                "channel_id": channel_id,
                "messages": [],
                "info": "No messages found in this channel.",
            })

        formatted = []
        for msg in messages:
            ts_str = msg.get("ts", "0")
            try:
                readable = datetime.fromtimestamp(
                    float(ts_str), tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, OSError):
                readable = ts_str

            formatted.append({
                "user":          msg.get("user") or msg.get("bot_id") or "unknown",
                "text":          msg.get("text", ""),
                "timestamp":     ts_str,
                "readable_time": readable,
            })

        return json.dumps({
            "channel":       channel,
            "channel_id":    channel_id,
            "message_count": len(formatted),
            "messages":      formatted,
        })

    def _resolve_channel_id(self, channel: str) -> str:
        import re
        channel = channel.lstrip("#")
        if re.fullmatch(r"[CGDW][A-Z0-9]+", channel):
            return channel

        cursor = None
        while True:
            kwargs: dict[str, Any] = {
                "types": "public_channel,private_channel",
                "exclude_archived": True,
                "limit": 200,
            }
            if cursor:
                kwargs["cursor"] = cursor

            resp = self._client.conversations_list(**kwargs)
            for ch in resp.get("channels", []):
                if ch["name"] == channel:
                    return ch["id"]

            next_cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not next_cursor:
                break
            cursor = next_cursor

        raise ValueError(f"Channel '{channel}' not found in workspace.")
