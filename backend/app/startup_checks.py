import logging
import sys

from app.config import Settings

log = logging.getLogger(__name__)


async def run_preflight_checks(settings: Settings) -> None:
    errors: list[str] = []

    await _check_gemini(settings, errors)
    await _check_slack(settings, errors)

    if errors:
        log.critical("[PREFLIGHT FAILED] The following checks did not pass:")
        for i, err in enumerate(errors, 1):
            log.critical("  [%d] %s", i, err)
        sys.exit(1)

    log.info("[CHECKPOINT: PREFLIGHT_PASS] All external dependency checks passed")


async def _check_gemini(settings: Settings, errors: list[str]) -> None:
    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)
        client.models.get(model=f"models/{settings.gemini_model}")
        log.info("[PREFLIGHT] Gemini model '%s' — OK", settings.gemini_model)
    except Exception as exc:
        errors.append(f"Gemini: {exc}")
        log.error("[PREFLIGHT] Gemini model '%s' — FAILED: %s", settings.gemini_model, exc)


async def _check_slack(settings: Settings, errors: list[str]) -> None:
    try:
        from slack_sdk import WebClient
        resp = WebClient(token=settings.slack_bot_token).auth_test()
        log.info("[PREFLIGHT] Slack token — OK (bot: %s)", resp.get("user"))
    except Exception as exc:
        errors.append(f"Slack: {exc}")
        log.error("[PREFLIGHT] Slack token — FAILED: %s", exc)
