import pytest

from app.ai.graph import AtlasGraph
from app.conversation.loader import ConversationLoader
from app.conversation.summarizer import Summarizer
from app.credentials.manager import CredentialManager
from app.orchestrator.provider import GitHubIssueProvider
from app.orchestrator.workflow_bridge import WorkflowBridge
from app.workflow.planner import Planner
from app.workflow.states import ConversationState


class DummySession:
    async def get(self, model, ident):
        return None

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def add(self, obj):
        return None


@pytest.mark.asyncio
async def test_conversation_loader_persists_messages():
    session = DummySession()
    loader = ConversationLoader(session)

    class DummyWorkspace:
        id = "workspace-1"

    session.get = lambda model, ident: (DummyWorkspace() if model.__name__ == "Workspace" else None)
    conv = await loader.load(
        workspace_id="workspace-1",
        platform="slack",
        external_thread_id="thread-1",
        channel_id="channel-1",
        messages=[{"id": "m1", "user_id": "u1", "text": "hello", "metadata": {"source": "slack"}}],
    )
    assert conv.platform == "slack"


@pytest.mark.asyncio
async def test_summarizer_returns_summary():
    summary = await Summarizer().summarize([{"text": "hello"}, {"text": "world"}])
    assert "Conversation summary" in summary


def test_credential_manager_round_trip():
    manager = CredentialManager(master_key="testkey12345678901234567890")
    encrypted = manager.encrypt("secret")
    assert manager.decrypt(encrypted) == "secret"


def test_planner_builds_issue_plan():
    planner = Planner()
    state = ConversationState(input_text="Create an issue in owner/repo about a login bug")
    planned = planner.build_plan(state)
    assert planned.plan["tool"] == "create_issue"


@pytest.mark.asyncio
async def test_workflow_bridge_runs_without_provider():
    bridge = WorkflowBridge()
    result = await bridge.run("hello")
    assert result.result == "No workflow action required"


@pytest.mark.asyncio
async def test_github_issue_provider_executes():
    provider = GitHubIssueProvider(token="fake-token")
    import unittest.mock as mock

    with mock.patch.object(provider._tool, "execute", return_value='{"number": 1, "url": "https://example.com"}') as mocked:
        value = await provider.create_issue({"repo": "owner/repo", "title": "t", "body": "b"})

    assert value.startswith("{")
    mocked.assert_awaited_once()


@pytest.mark.asyncio
async def test_atlas_graph_builds_structured_action_plan():
    graph = AtlasGraph()
    state = await graph.run("Please create an issue in owner/repo about a login bug")

    assert state.summary
    assert state.tool_name == "create_issue"
    assert state.tool_arguments is not None
    assert state.reply
