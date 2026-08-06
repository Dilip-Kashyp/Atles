import logging
from fastapi import APIRouter, Depends, Request, Response

from app.dependencies import get_orchestrator, get_slack_platform
from app.orchestrator.agent import Orchestrator
from app.orchestrator.platform_base import ChatPlatform, NormalizedEvent

log = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["Slack Events"])


@router.post("/events")
async def slack_events(
    request: Request,
    platform: ChatPlatform = Depends(get_slack_platform),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> Response:
    log.info("[CHECKPOINT: SLACK_EVENT_HIT] Received POST /slack/events")

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

    return await platform.handle_request(request, _background_dispatch)
