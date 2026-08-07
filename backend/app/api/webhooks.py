import logging

from fastapi import APIRouter, Depends, Request, Response

from app.dependencies import get_slack_platform
from app.orchestrator.platform_base import ChatPlatform

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/slack")
async def slack_webhook(
    request: Request,
    platform: ChatPlatform = Depends(get_slack_platform),
) -> Response:
    log.info("[CHECKPOINT: WEBHOOK_SLACK] Received Slack webhook")

    async def _dispatch(event, plat):
        await plat.send_reply(event.channel, event.thread_ts, "Webhook received")

    return await platform.handle_request(request, _dispatch)
