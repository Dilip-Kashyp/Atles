import asyncio
import hashlib
import hmac
import logging
import re
import time
from collections import deque
from typing import Any, Callable, Coroutine

from fastapi import HTTPException, Request, Response
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import Settings
from app.orchestrator.platform_base import ChatPlatform, NormalizedEvent

log = logging.getLogger(__name__)


class SlackPlatform(ChatPlatform):
    def __init__(self, settings: Settings, client: WebClient) -> None:
        self.settings = settings
        self.client = client
        self._seen_event_ids: deque[str] = deque(maxlen=512)
        self._bot_user_id: str | None = None

    async def handle_request(
        self,
        request: Request,
        dispatch_func: Callable[[NormalizedEvent, ChatPlatform], Coroutine[Any, Any, None]],
    ) -> Response:
        log.info("[CHECKPOINT: SLACK_INGRESS] Incoming Slack webhook request")
        body_bytes = await request.body()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        if not self._verify_signature(body_bytes, timestamp, signature):
            log.warning("[CHECKPOINT: SLACK_AUTH_FAIL] Invalid Slack signature")
            raise HTTPException(status_code=403, detail="Invalid Slack signature.")

        log.info("[CHECKPOINT: SLACK_AUTH_PASS] Valid signature confirmed")

        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload.")

        payload_type = payload.get("type")

        if payload_type == "url_verification":
            log.info("[CHECKPOINT: SLACK_HANDSHAKE] URL verification challenge received")
            return Response(content=payload.get("challenge", ""), media_type="text/plain")

        if payload_type == "event_callback":
            event = payload.get("event", {})
            if event.get("type") != "app_mention":
                return Response(content="ok", media_type="text/plain")

            event_ts = event.get("event_ts") or event.get("ts", "")
            if self._already_seen(event_ts):
                log.info("[CHECKPOINT: SLACK_DEDUP] Skipping duplicate event_ts: %s", event_ts)
                return Response(content="ok", media_type="text/plain")

            norm_event = NormalizedEvent(
                channel=event.get("channel", ""),
                thread_ts=event.get("thread_ts") or event.get("ts", ""),
                sender=event.get("user", ""),
                raw_text=self._strip_mention(event.get("text", "")),
                event_id=event_ts,
                workspace_id=payload.get("team_id", ""),
            )

            log.info("[CHECKPOINT: SLACK_DISPATCH] Spawning background task for mention")
            asyncio.create_task(dispatch_func(norm_event, self))
            return Response(content="ok", media_type="text/plain")

        return Response(content="ok", media_type="text/plain")

    def _verify_signature(self, request_body: bytes, timestamp: str, signature: str) -> bool:
        if not self.settings.slack_signing_secret:
            return True

        try:
            ts_int = int(timestamp)
        except (TypeError, ValueError):
            return False

        if abs(time.time() - ts_int) > 300:
            return False

        base_string = f"v0:{timestamp}:{request_body.decode('utf-8')}"
        expected_sig = (
            "v0="
            + hmac.new(
                self.settings.slack_signing_secret.encode("utf-8"),
                base_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        )

        return hmac.compare_digest(expected_sig, signature)

    def _already_seen(self, event_id: str) -> bool:
        if event_id in self._seen_event_ids:
            return True
        self._seen_event_ids.append(event_id)
        return False

    def _strip_mention(self, raw_text: str) -> str:
        bot_id = self._bot_user_id or ""
        if bot_id:
            question = re.sub(rf"<@{re.escape(bot_id)}>", "", raw_text, count=1).strip()
        else:
            question = re.sub(r"<@[A-Z0-9]+>", "", raw_text, count=1).strip()

        return question or "Hello! How can I help you?"

    async def validate_startup(self) -> None:
        if self.settings.slack_bot_user_id:
            self._bot_user_id = self.settings.slack_bot_user_id
            return

        try:
            resp = self.client.auth_test()
            self._bot_user_id = resp["user_id"]
            log.info("[CHECKPOINT: SLACK_STARTUP] Auto-resolved bot user ID: %s", self._bot_user_id)
        except SlackApiError as exc:
            log.error("[CHECKPOINT: SLACK_STARTUP_WARN] auth.test failed: %s", exc.response.get("error"))

    async def send_typing_indicator(self, channel: str, thread_ts: str) -> None:
        try:
            self.client.chat_postMessage(channel=channel, thread_ts=thread_ts, text="⏳ Thinking…")
        except SlackApiError:
            pass

    async def send_reply(self, channel: str, thread_ts: str, text: str) -> None:
        try:
            self.client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)
            log.info("[CHECKPOINT: SLACK_EGRESS] Posted reply to thread: %s", thread_ts)
        except SlackApiError as exc:
            log.error("[CHECKPOINT: SLACK_EGRESS_ERROR] Failed to post reply: %s", exc.response.get("error"))
