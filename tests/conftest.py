import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def _stub_settings(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-signing-secret")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-flash")
    monkeypatch.setenv("MEMORY_ENABLED", "false")
    monkeypatch.setenv("MONGODB_URI", "")
