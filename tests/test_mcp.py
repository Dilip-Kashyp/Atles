import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestToolDispatcher:

    @pytest.fixture
    def dispatcher(self):
        from app.orchestrator.tool_dispatcher import ToolDispatcher
        return ToolDispatcher()

    def _make_tool(self, name: str, result: str = "ok") -> MagicMock:
        tool = MagicMock()
        tool.name = name
        tool.description = f"Mock tool {name}"
        tool.input_schema = {"type": "object", "properties": {}}
        tool.execute = AsyncMock(return_value=result)
        return tool

    def test_register_adds_tool_to_registry(self, dispatcher):
        tool = self._make_tool("my_tool")
        dispatcher.register(tool)
        assert "my_tool" in [t.name for t in dispatcher.get_all_tools()]

    def test_register_multiple_tools(self, dispatcher):
        for name in ("tool_a", "tool_b", "tool_c"):
            dispatcher.register(self._make_tool(name))
        assert len(dispatcher.get_all_tools()) == 3

    def test_register_overwrites_duplicate_name(self, dispatcher):
        dispatcher.register(self._make_tool("dup", result="first"))
        dispatcher.register(self._make_tool("dup", result="second"))
        assert len(dispatcher.get_all_tools()) == 1

    def test_get_all_tools_empty_initially(self, dispatcher):
        assert dispatcher.get_all_tools() == []

    @pytest.mark.asyncio
    async def test_execute_calls_registered_tool(self, dispatcher):
        tool = self._make_tool("ping", result="pong")
        dispatcher.register(tool)
        result = await dispatcher.execute("ping", {})
        tool.execute.assert_awaited_once_with({})
        assert result == "pong"

    @pytest.mark.asyncio
    async def test_execute_passes_arguments_to_tool(self, dispatcher):
        tool = self._make_tool("open_issue")
        dispatcher.register(tool)
        args = {"repo": "owner/repo", "title": "Bug", "body": "Details"}
        await dispatcher.execute("open_issue", args)
        tool.execute.assert_awaited_once_with(args)

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_raises_value_error(self, dispatcher):
        with pytest.raises(ValueError, match="not found in registry"):
            await dispatcher.execute("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_execute_logs_and_returns_result(self, dispatcher):
        tool = self._make_tool("find_document", result='{"title": "API Docs"}')
        dispatcher.register(tool)
        result = await dispatcher.execute("find_document", {"query": "API"})
        assert result == '{"title": "API Docs"}'

    @pytest.mark.asyncio
    async def test_register_mcp_client_no_input_schema(self, dispatcher):
        assert not hasattr(dispatcher, "register_mcp_client_tools")


class TestSlackReadMessagesTool:

    @pytest.fixture
    def client_with_tools(self):
        with patch("app.llm.gemini.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            from app.llm.gemini import GeminiClient
            from app.tools.github import GithubIssueTool
            yield GeminiClient(
                api_key="fake-key",
                model_name="gemini-test-flash",
                tools=[GithubIssueTool(token="fake-token")],
            )

    @pytest.fixture
    def mock_slack_client(self):
        client = MagicMock()
        client.conversations_list.return_value = {
            "channels": [{"name": "general", "id": "C123"}],
            "response_metadata": {"next_cursor": ""},
        }
        client.conversations_history.return_value = {
            "messages": [
                {"user": "U1", "text": "Hello!", "ts": "1700000000.000"},
                {"user": "U2", "text": "World!", "ts": "1700000001.000"},
            ]
        }
        return client

    @pytest.fixture
    def tool(self, mock_slack_client):
        from app.tools.slack import SlackReadMessagesTool
        return SlackReadMessagesTool(client=mock_slack_client)

    def test_name_is_read_messages(self, tool):
        assert tool.name == "read_messages"

    def test_description_mentions_slack(self, tool):
        assert "slack" in tool.description.lower() or "channel" in tool.description.lower()

    def test_input_schema_requires_channel(self, tool):
        assert "channel" in tool.input_schema["required"]

    def test_input_schema_has_limit_with_default(self, tool):
        assert "limit" in tool.input_schema["properties"]
        assert tool.input_schema["properties"]["limit"].get("default") == 20

    @pytest.mark.asyncio
    async def test_execute_resolves_channel_name_to_id(self, tool, mock_slack_client):
        result_str = await tool.execute({"channel": "general"})
        result = json.loads(result_str)
        mock_slack_client.conversations_history.assert_called_once_with(
            channel="C123", limit=20
        )
        assert result["message_count"] == 2

    @pytest.mark.asyncio
    async def test_execute_passes_through_channel_id(self, tool, mock_slack_client):
        result_str = await tool.execute({"channel": "C123"})
        result = json.loads(result_str)
        assert result["channel_id"] == "C123"
        mock_slack_client.conversations_list.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_returns_messages(self, tool):
        result_str = await tool.execute({"channel": "C123"})
        result = json.loads(result_str)
        assert result["message_count"] == 2
        assert result["messages"][0]["text"] == "Hello!"

    @pytest.mark.asyncio
    async def test_execute_respects_limit_cap_at_100(self, tool, mock_slack_client):
        await tool.execute({"channel": "C123", "limit": 999})
        mock_slack_client.conversations_history.assert_called_once_with(
            channel="C123", limit=100
        )

    @pytest.mark.asyncio
    async def test_execute_channel_not_found_returns_error_json(self, tool, mock_slack_client):
        mock_slack_client.conversations_list.return_value = {
            "channels": [],
            "response_metadata": {"next_cursor": ""},
        }
        result_str = await tool.execute({"channel": "nonexistent"})
        result = json.loads(result_str)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_empty_channel_returns_info_json(self, tool, mock_slack_client):
        mock_slack_client.conversations_history.return_value = {"messages": []}
        result_str = await tool.execute({"channel": "C123"})
        result = json.loads(result_str)
        assert result["messages"] == []
        assert "info" in result


class TestGithubIssueTool:

    @pytest.fixture
    def tool(self):
        from app.tools.github import GithubIssueTool
        return GithubIssueTool(token="fake-github-token")

    def test_name_is_open_issue(self, tool):
        assert tool.name == "open_issue"

    def test_description_mentions_github(self, tool):
        assert "issue" in tool.description.lower() or "github" in tool.description.lower()

    def test_input_schema_type_is_object(self, tool):
        assert tool.input_schema["type"] == "object"

    def test_input_schema_has_required_fields(self, tool):
        required = tool.input_schema.get("required", [])
        assert "repo" in required
        assert "title" in required
        assert "body" in required

    def test_input_schema_properties_have_string_types(self, tool):
        props = tool.input_schema["properties"]
        for field in ("repo", "title", "body"):
            assert props[field]["type"] == "string"

    @pytest.mark.asyncio
    async def test_execute_creates_issue_via_pygithub(self, tool):
        expected = json.dumps({
            "number": 42, "title": "Bug",
            "url": "https://github.com/owner/repo/issues/42", "state": "open",
        })
        with patch.object(tool, "_create_issue", return_value=expected):
            result = await tool.execute({"repo": "owner/repo", "title": "Bug", "body": "Details"})
        data = json.loads(result)
        assert data["number"] == 42
        assert "url" in data

    @pytest.mark.asyncio
    async def test_execute_returns_error_json_on_github_exception(self, tool):
        from github.GithubException import GithubException
        exc = GithubException(422, {"message": "Validation Failed"}, {})
        with patch.object(tool, "_create_issue", side_effect=exc):
            result = await tool.execute({"repo": "owner/repo", "title": "T", "body": "B"})
        data = json.loads(result)
        assert "error" in data
        assert "Validation Failed" in data["error"]


class TestNotionSearchTool:

    @pytest.fixture
    def tool(self):
        from app.tools.notion import NotionSearchTool
        return NotionSearchTool(token="fake-notion-token")

    def test_name_is_find_document(self, tool):
        assert tool.name == "find_document"

    def test_description_mentions_notion(self, tool):
        assert "notion" in tool.description.lower() or "document" in tool.description.lower()

    def test_input_schema_type_is_object(self, tool):
        assert tool.input_schema["type"] == "object"

    def test_input_schema_requires_query(self, tool):
        assert "query" in tool.input_schema.get("required", [])

    def test_query_property_is_string(self, tool):
        assert tool.input_schema["properties"]["query"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_execute_returns_results_json(self, tool):
        fake_response = {
            "results": [
                {
                    "id": "page-1",
                    "url": "https://notion.so/page-1",
                    "properties": {
                        "Name": {
                            "type": "title",
                            "title": [{"plain_text": "API Docs"}],
                        }
                    },
                }
            ]
        }
        with patch("app.tools.notion.AsyncClient") as MockClient:
            instance = MockClient.return_value
            instance.search = AsyncMock(return_value=fake_response)
            result_str = await tool.execute({"query": "API docs"})

        data = json.loads(result_str)
        assert data["count"] == 1
        assert data["results"][0]["title"] == "API Docs"
        assert "notion.so" in data["results"][0]["url"]

    @pytest.mark.asyncio
    async def test_execute_returns_empty_when_no_results(self, tool):
        with patch("app.tools.notion.AsyncClient") as MockClient:
            instance = MockClient.return_value
            instance.search = AsyncMock(return_value={"results": []})
            result_str = await tool.execute({"query": "nonexistent"})

        data = json.loads(result_str)
        assert data["results"] == []
        assert "info" in data

    @pytest.mark.asyncio
    async def test_execute_returns_error_json_on_api_failure(self, tool):
        from notion_client.errors import APIResponseError
        with patch("app.tools.notion.AsyncClient") as MockClient:
            instance = MockClient.return_value
            instance.search = AsyncMock(side_effect=Exception("Network error"))
            result_str = await tool.execute({"query": "anything"})

        data = json.loads(result_str)
        assert "error" in data


class TestMemoryUtilParsers:

    def test_extract_issue_number_from_json(self):
        from app.memory.manager import _extract_issue_number
        result_str = '{"number": 42, "url": "https://github.com/owner/repo/issues/42"}'
        assert _extract_issue_number(result_str) == "42"

    def test_extract_issue_number_missing_returns_empty(self):
        from app.memory.manager import _extract_issue_number
        assert _extract_issue_number("no number here") == ""

    def test_extract_pr_number_from_json(self):
        from app.memory.manager import _extract_pr_number
        result_str = '{"number": 17, "title": "Fix auth"}'
        assert _extract_pr_number(result_str) == "17"

    def test_extract_jira_key_standard_format(self):
        from app.memory.manager import _extract_jira_key
        assert _extract_jira_key("Created ticket PROJ-123") == "PROJ-123"

    def test_extract_jira_key_missing_returns_empty(self):
        from app.memory.manager import _extract_jira_key
        assert _extract_jira_key("no jira key") == ""
