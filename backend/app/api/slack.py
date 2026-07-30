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
        try:
            result = await orchestrator.process(event.raw_text)
            answer = result.response
        except Exception as exc:
            log.exception("[CHECKPOINT: BG_ORCHESTRATOR_ERROR] Failed for event %s", event.event_id)
            answer = f"❌ Error processing request: `{type(exc).__name__}: {exc}`"

        await plat.send_reply(event.channel, event.thread_ts, answer)

    return await platform.handle_request(request, _background_dispatch)
