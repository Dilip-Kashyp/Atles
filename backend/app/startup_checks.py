import logging
import sys

from app.config import Settings

log = logging.getLogger(__name__)


async def run_preflight_checks(settings: Settings) -> None:
    errors: list[str] = []

    await _check_gemini(settings, errors)
    await _check_slack(settings, errors)
    await _check_github(settings, errors)
    await _check_notion(settings, errors)

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
        from slack_sdk.errors import SlackApiError
        resp = WebClient(token=settings.slack_bot_token).auth_test()
        log.info("[PREFLIGHT] Slack token — OK (bot: %s)", resp.get("user"))
    except Exception as exc:
        errors.append(f"Slack: {exc}")
        log.error("[PREFLIGHT] Slack token — FAILED: %s", exc)


async def _check_github(settings: Settings, errors: list[str]) -> None:
    if not settings.github_token:
        log.info("[PREFLIGHT] GitHub token — SKIPPED (not configured)")
        return

    try:
        from github import Github
        user = Github(settings.github_token).get_user()
        log.info("[PREFLIGHT] GitHub token — OK (user: %s)", user.login)
    except Exception as exc:
        errors.append(f"GitHub: {exc}")
        log.error("[PREFLIGHT] GitHub token — FAILED: %s", exc)


async def _check_notion(settings: Settings, errors: list[str]) -> None:
    if not settings.notion_token:
        log.info("[PREFLIGHT] Notion token — SKIPPED (not configured)")
        return

    try:
        from notion_client import Client
        Client(auth=settings.notion_token).users.me()
        log.info("[PREFLIGHT] Notion token — OK")
    except Exception as exc:
        errors.append(f"Notion: {exc}")
        log.error("[PREFLIGHT] Notion token — FAILED: %s", exc)
