import asyncio
import hashlib
import hmac
import logging
import re
import time
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import HTTPException, Request, Response
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import Settings
from app.domain.shared.exceptions import DeduplicationUnavailableError
from app.infrastructure.cache.redis import redis_client
from app.orchestrator.platform_base import ChatPlatform, NormalizedEvent

log = logging.getLogger(__name__)


class SlackPlatform(ChatPlatform):
    def __init__(self, client: WebClient, bot_user_id: str | None = None) -> None:
        self.client = client
        self._bot_user_id = bot_user_id

    async def handle_request(
        self,
        request: Request,
        dispatch_func: Callable[[NormalizedEvent, ChatPlatform], Coroutine[Any, Any, None]],
    ) -> Response:
        raise NotImplementedError("Use SlackWebhookHandler for ingress")

    async def send_typing_indicator(self, channel: str, thread_ts: str) -> None:
        try:
            
            
            
            
            await asyncio.to_thread(
                self.client.chat_postMessage,
                channel=channel, 
                thread_ts=thread_ts, 
                text="⏳ Thinking…"
            )
        except SlackApiError:
            pass

    async def send_reply(self, channel: str, thread_ts: str, text: str) -> None:
        try:
            
            
            
            
            await asyncio.to_thread(
                self.client.chat_postMessage,
                channel=channel, 
                thread_ts=thread_ts, 
                text=text
            )
            log.info("[CHECKPOINT: SLACK_EGRESS] Posted reply to thread: %s", thread_ts)
        except SlackApiError as exc:
            log.error("[CHECKPOINT: SLACK_EGRESS_ERROR] Failed to post reply: %s", exc.response.get("error"))


class SlackWebhookHandler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def parse_and_verify(self, request: Request) -> dict[str, Any] | Response:
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
            
        return payload
        
    async def normalize_event(self, payload: dict[str, Any], bot_user_id: str | None = None) -> NormalizedEvent | Response:
        event = payload.get("event", {})
        if event.get("type") != "app_mention":
            return Response(content="ok", media_type="text/plain")

        event_ts = event.get("event_ts") or event.get("ts", "")
        if await self._already_seen(event_ts):
            log.info("[CHECKPOINT: SLACK_DEDUP] Skipping duplicate event_ts: %s", event_ts)
            return Response(content="ok", media_type="text/plain")

        
        raw_text = event.get("text", "")
        if bot_user_id:
            question = re.sub(rf"<@{re.escape(bot_user_id)}>", "", raw_text, count=1).strip()
        else:
            question = re.sub(r"<@[A-Z0-9]+>", "", raw_text, count=1).strip()
            
        question = question or "Hello! How can I help you?"

        return NormalizedEvent(
            channel=event.get("channel", ""),
            thread_ts=event.get("thread_ts") or event.get("ts", ""),
            sender=event.get("user", ""),
            raw_text=question,
            event_id=event_ts,
            workspace_id=payload.get("team_id", ""),
        )

    def _verify_signature(self, request_body: bytes, timestamp: str, signature: str) -> bool:
        if not self.settings.slack_signing_secret:
            return True

        try:
            ts_int = int(timestamp)
        except (TypeError, ValueError):
            return False

        if abs(time.time() - ts_int) > self.settings.slack_timestamp_tolerance_seconds:
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

    async def _already_seen(self, event_id: str) -> bool:
        
        try:
            is_new = await redis_client.set(
                f"slack_event:{event_id}", 
                "1", 
                nx=True, 
                ex=self.settings.slack_dedup_ttl_seconds
            )
            return not is_new
        except Exception as exc:
            if self.settings.slack_dedup_fail_mode == "closed":
                log.error("[CHECKPOINT: REDIS_FAIL_CLOSED] Deduplication unavailable. Rejecting event.")
                raise DeduplicationUnavailableError("Redis is unreachable.") from exc
            
            log.warning("[CHECKPOINT: REDIS_FAIL_OPEN] Redis deduplication failed, proceeding to process event: %s", exc)
            return False
