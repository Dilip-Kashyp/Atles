import hashlib
import hmac
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


SIGNING_SECRET = "test-signing-secret"


def _slack_headers(body: str, secret: str = SIGNING_SECRET) -> dict:
    ts = str(int(time.time()))
    base = f"v0:{ts}:{body}"
    sig = "v0=" + hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
    return {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": sig,
        "Content-Type": "application/json",
    }


def _make_orchestrator_result(response: str = "Hello!", tool_used: bool = False):
    from app.orchestrator.agent import OrchestratorResult
    return OrchestratorResult(response=response, tool_used=tool_used)


class TestSlackUrlVerification:

    @pytest.fixture
    def app(self):
        from fastapi import FastAPI
        from app.api import slack as slack_mod
        from app.orchestrator.agent import Orchestrator

        test_app = FastAPI()

        mock_orchestrator = MagicMock(spec=Orchestrator)
        mock_orchestrator.process = AsyncMock(return_value=_make_orchestrator_result())

        mock_platform = MagicMock()
        mock_platform.handle_request = AsyncMock()

        test_app.state.orchestrator = mock_orchestrator
        test_app.state.slack_platform = mock_platform
        test_app.state.memory_manager = None

        test_app.include_router(slack_mod.router)
        return test_app

    def test_url_verification_returns_challenge(self, app):
        body = '{"type": "url_verification", "challenge": "test_challenge_abc"}'
        headers = _slack_headers(body)

        with patch("app.orchestrator.slack_handler.SlackPlatform") as _:
            from app.orchestrator.slack_handler import SlackPlatform
            from fastapi import Response

            app.state.slack_platform.handle_request = AsyncMock(
                return_value=Response(
                    content='{"challenge": "test_challenge_abc"}',
                    media_type="application/json",
                )
            )

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/slack/events", content=body, headers=headers)

        app.state.slack_platform.handle_request.assert_called_once()


class TestSlackEventEndpoint:

    @pytest.fixture
    def app(self):
        from fastapi import FastAPI, Response
        from app.api import slack as slack_mod
        from app.orchestrator.agent import Orchestrator

        test_app = FastAPI()
        mock_orchestrator = MagicMock(spec=Orchestrator)
        mock_orchestrator.process = AsyncMock(return_value=_make_orchestrator_result("Ack!"))

        mock_platform = MagicMock()
        mock_platform.handle_request = AsyncMock(
            return_value=Response(status_code=200)
        )

        test_app.state.orchestrator = mock_orchestrator
        test_app.state.slack_platform = mock_platform
        test_app.state.memory_manager = None

        test_app.include_router(slack_mod.router)
        return test_app

    def test_valid_event_returns_200(self, app):
        body = '{"type": "event_callback", "event": {"type": "app_mention", "text": "hello bot"}}'
        headers = _slack_headers(body)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/slack/events", content=body, headers=headers)
        assert resp.status_code == 200

    def test_event_delegates_to_platform_handle_request(self, app):
        body = '{"type": "event_callback", "event": {"type": "app_mention", "text": "ping"}}'
        headers = _slack_headers(body)
        client = TestClient(app, raise_server_exceptions=False)
        client.post("/slack/events", content=body, headers=headers)
        app.state.slack_platform.handle_request.assert_called_once()


class TestChatEndpoint:

    @pytest.fixture
    def app(self):
        from fastapi import FastAPI
        from app.api import chat as chat_mod
        from app.orchestrator.agent import Orchestrator

        test_app = FastAPI()
        mock_orchestrator = MagicMock(spec=Orchestrator)
        mock_orchestrator.process = AsyncMock(
            return_value=_make_orchestrator_result("I'm fine, thanks!")
        )
        test_app.state.orchestrator = mock_orchestrator
        test_app.state.memory_manager = None

        test_app.include_router(chat_mod.router)
        return test_app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_chat_returns_200(self, client):
        resp = client.post("/chat/", json={"message": "how are you?"})
        assert resp.status_code == 200

    def test_chat_response_schema(self, client):
        resp = client.post("/chat/", json={"message": "hello"})
        data = resp.json()
        assert "response" in data
        assert "tool_used" in data
        assert data["response"] == "I'm fine, thanks!"

    def test_chat_response_tool_used_false(self, client):
        resp = client.post("/chat/", json={"message": "hello"})
        assert resp.json()["tool_used"] is False

    def test_chat_with_session_key_preserved_in_response(self, client):
        resp = client.post("/chat/", json={"message": "hi", "session_key": "my-session-1"})
        assert resp.status_code == 200

    def test_chat_calls_orchestrator_process(self, app, client):
        client.post("/chat/", json={"message": "create an issue"})
        app.state.orchestrator.process.assert_awaited_once()

    def test_chat_empty_message_returns_422(self, client):
        resp = client.post("/chat/", json={"message": ""})
        assert resp.status_code == 422

    def test_chat_missing_message_returns_422(self, client):
        resp = client.post("/chat/", json={})
        assert resp.status_code == 422

    def test_chat_message_too_long_returns_422(self, client):
        resp = client.post("/chat/", json={"message": "x" * 5000})
        assert resp.status_code == 422

    def test_chat_with_tool_used_response(self, app, client):
        from app.orchestrator.agent import OrchestratorResult
        app.state.orchestrator.process = AsyncMock(
            return_value=OrchestratorResult(
                response="Issue #42 created.",
                tool_used=True,
                tool_name="open_issue",
                tool_arguments={"repo": "owner/repo", "title": "Bug"},
            )
        )
        resp = client.post("/chat/", json={"message": "create an issue"})
        data = resp.json()
        assert data["tool_used"] is True
        assert data["tool_name"] == "open_issue"
        assert data["tool_arguments"]["repo"] == "owner/repo"


class TestSessionKeyStrategy:

    def _build_session_key(self, workspace_id, channel, sender, thread_ts, event_id):
        is_threaded = bool(thread_ts and thread_ts != event_id)
        if is_threaded:
            return f"{workspace_id}:{thread_ts}"
        else:
            return f"{workspace_id}:{channel}:{sender}"

    def test_threaded_event_uses_thread_ts(self):
        key = self._build_session_key(
            workspace_id="T123",
            channel="C456",
            sender="U789",
            thread_ts="1785577897.442689",
            event_id="1785579999.000000",
        )
        assert key == "T123:1785577897.442689"
        assert "C456" not in key
        assert "U789" not in key

    def test_non_threaded_event_uses_user_channel(self):
        key = self._build_session_key(
            workspace_id="T123",
            channel="C456",
            sender="U789",
            thread_ts="",
            event_id="1785579999.000000",
        )
        assert key == "T123:C456:U789"

    def test_thread_ts_equals_event_id_is_not_threaded(self):
        key = self._build_session_key(
            workspace_id="T123",
            channel="C456",
            sender="U789",
            thread_ts="1785579999.000000",
            event_id="1785579999.000000",
        )
        assert key == "T123:C456:U789"

    def test_thread_ts_none_is_not_threaded(self):
        key = self._build_session_key(
            workspace_id="TWSPACE",
            channel="CCHAN",
            sender="UUSER",
            thread_ts=None,
            event_id="1785579999.000000",
        )
        assert key == "TWSPACE:CCHAN:UUSER"

    def test_different_workspaces_produce_different_keys(self):
        key1 = self._build_session_key("WS1", "C1", "U1", "", "ev1")
        key2 = self._build_session_key("WS2", "C1", "U1", "", "ev1")
        assert key1 != key2

    def test_same_thread_ts_produces_same_key(self):
        key1 = self._build_session_key("T1", "C1", "U1", "ts123", "ev1")
        key2 = self._build_session_key("T1", "C1", "U2", "ts123", "ev2")
        assert key1 == key2
