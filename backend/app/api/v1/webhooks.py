import logging

from fastapi import APIRouter, Request, Response

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(request: Request) -> Response:
    log.info("[CHECKPOINT: WEBHOOK_GITHUB] Received GitHub webhook event")
    try:
        payload = await request.json()
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        log.info("[CHECKPOINT: WEBHOOK_GITHUB_EVENT] event=%s action=%s", event_type, payload.get("action"))
    except Exception:
        log.warning("[CHECKPOINT: WEBHOOK_GITHUB_WARN] Non-JSON or ping payload received")

    return Response(content="ok", media_type="text/plain")
