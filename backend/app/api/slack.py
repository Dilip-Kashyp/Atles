import asyncio
import logging
from fastapi import APIRouter, Depends, Request, Response
from slack_sdk import WebClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.dependencies import get_orchestrator, get_slack_webhook_handler
from app.orchestrator.agent import Orchestrator
from app.orchestrator.slack_handler import SlackWebhookHandler, SlackPlatform
from app.orchestrator.platform_base import ChatPlatform, NormalizedEvent
from app.models.integrations import Integration
from app.credentials.manager import CredentialManager

log = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["Slack Events"])


@router.post("/events")
async def slack_events(
    request: Request,
    handler: SlackWebhookHandler = Depends(get_slack_webhook_handler),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db),
) -> Response:
    # 1. Parse payload and verify signature
    payload = await handler.parse_and_verify(request)
    if isinstance(payload, Response):
        return payload

    team_id = payload.get("team_id")
    if not team_id:
        return Response(content="ok", media_type="text/plain")

    # 2. Look up the Atlas Workspace Integration for this Slack team
    result = await db.execute(
        select(Integration)
        .where(
            Integration.provider_type == "slack",
            Integration.provider_workspace_id == team_id
        )
        .options(selectinload(Integration.credentials))
    )
    integration = result.scalars().first()

    if not integration or not integration.credentials:
        log.warning("[CHECKPOINT: SLACK_AUTH_WARN] Ignored webhook from unconnected team_id %s", team_id)
        return Response(content="ok", media_type="text/plain")

    # 3. Decrypt token and construct local platform client
    cred_manager = CredentialManager()
    encrypted_token = integration.credentials[0].encrypted_token
    bot_token = cred_manager.decrypt(encrypted_token)

    if not bot_token:
        log.error("[CHECKPOINT: SLACK_AUTH_ERR] Failed to decrypt token for team %s", team_id)
        return Response(content="ok", media_type="text/plain")

    client = WebClient(token=bot_token)
    platform = SlackPlatform(client=client)

    # 4. Normalize the event
    norm_event = handler.normalize_event(payload)
    if isinstance(norm_event, Response):
        return norm_event

    # Use the Atlas Workspace ID instead of Slack Team ID for internal session mapping
    norm_event.workspace_id = str(integration.workspace_id)

    async def _background_dispatch(event: NormalizedEvent, plat: ChatPlatform) -> None:
        await plat.send_typing_indicator(event.channel, event.thread_ts)

        session_context = None
        memory_manager = getattr(request.app.state, "memory_manager", None)
        if memory_manager is not None:
            from app.memory.models import SessionContext

            is_threaded = bool(event.thread_ts and event.thread_ts != event.event_id)
            if is_threaded:
                session_key = f"{event.workspace_id}:{event.thread_ts}"
            else:
                session_key = f"{event.workspace_id}:{event.channel}:{event.sender}"

            session_context = SessionContext(
                session_key=session_key,
                workspace_id=event.workspace_id,
                user_id=event.sender,
                channel_id=event.channel,
                thread_ts=event.thread_ts,
            )
            log.info(
                "[CHECKPOINT: SLACK_SESSION_BUILT] session_key=%s", session_key
            )

        try:
            result = await orchestrator.process(
                event.raw_text,
                session_context=session_context,
            )
            from app.utils.response_formatter import format_response
            answer = await format_response(result.response)
        except Exception as exc:
            log.exception("[CHECKPOINT: BG_ORCHESTRATOR_ERROR] Failed for event %s", event.event_id)
            from app.utils.response_formatter import format_error
            answer = await format_error(exc)

        await plat.send_reply(event.channel, event.thread_ts, answer)

    log.info("[CHECKPOINT: SLACK_DISPATCH] Spawning background task for mention")
    asyncio.create_task(_background_dispatch(norm_event, platform))
    
    return Response(content="ok", media_type="text/plain")
