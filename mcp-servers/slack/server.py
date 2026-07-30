import json
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[SlackMCP] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
if not SLACK_BOT_TOKEN:
    log.error("SLACK_BOT_TOKEN is not set.")

slack = WebClient(token=SLACK_BOT_TOKEN)

mcp = FastMCP(
    name="slack-mcp-server",
    instructions="Exposes tools for reading Slack workspace messages.",
)


def _resolve_channel_id(channel: str) -> str:
    channel = channel.lstrip("#")
    if channel.upper().startswith(("C", "G", "D")):
        return channel

    try:
        cursor = None
        while True:
            kwargs: dict = {
                "types": "public_channel,private_channel",
                "exclude_archived": True,
                "limit": 200,
            }
            if cursor:
                kwargs["cursor"] = cursor

            response = slack.conversations_list(**kwargs)
            for ch in response.get("channels", []):
                if ch["name"] == channel:
                    return ch["id"]

            next_cursor = response.get("response_metadata", {}).get("next_cursor")
            if not next_cursor:
                break
            cursor = next_cursor

    except SlackApiError as exc:
        log.error("conversations_list failed: %s", exc.response["error"])
        raise ValueError(f"Slack API error while listing channels: {exc.response['error']}") from exc

    raise ValueError(f"Channel '{channel}' not found.")


@mcp.tool()
def read_messages(channel: str, limit: int = 20) -> str:
    limit = max(1, min(limit, 100))

    try:
        channel_id = _resolve_channel_id(channel)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    try:
        response = slack.conversations_history(
            channel=channel_id,
            limit=limit,
        )
    except SlackApiError as exc:
        error_code = exc.response["error"]
        log.error("conversations_history failed: %s", error_code)
        return json.dumps({"error": f"Slack API error: {error_code}"})

    messages = response.get("messages", [])
    if not messages:
        return json.dumps({"messages": [], "info": "No messages found in this channel."})

    formatted = []
    for msg in messages:
        ts_str = msg.get("ts", "0")
        try:
            from datetime import datetime, timezone
            ts_float = float(ts_str)
            readable = datetime.fromtimestamp(ts_float, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
        except (ValueError, OSError):
            readable = ts_str

        formatted.append(
            {
                "user": msg.get("user") or msg.get("bot_id") or "unknown",
                "text": msg.get("text", ""),
                "timestamp": ts_str,
                "readable_time": readable,
            }
        )

    return json.dumps(
        {
            "channel": channel,
            "channel_id": channel_id,
            "message_count": len(formatted),
            "messages": formatted,
        }
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
