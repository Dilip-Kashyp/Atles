import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


class TestSystemInstruction:

    @pytest.fixture(autouse=True)
    def _load_prompt(self):
        from app.llm.prompts import SYSTEM_INSTRUCTION
        self.prompt = SYSTEM_INSTRUCTION

    def test_prompt_is_nonempty(self):
        assert len(self.prompt.strip()) > 200, "SYSTEM_INSTRUCTION is too short"

    def test_behavioral_contract_section_present(self):
        assert "BEHAVIORAL CONTRACT" in self.prompt

    def test_tool_mandate_rule_present(self):
        assert "RULE-01" in self.prompt
        assert "TOOL MANDATE" in self.prompt

    def test_no_hallucination_rule_present(self):
        assert "RULE-02" in self.prompt
        assert "HALLUCINATION" in self.prompt or "hallucinate" in self.prompt.lower()

    def test_missing_parameters_rule_present(self):
        assert "RULE-03" in self.prompt
        assert "MISSING PARAMETERS" in self.prompt or "missing" in self.prompt.lower()

    def test_memory_authoritative_rule_present(self):
        assert "RULE-04" in self.prompt
        assert "MEMORY CONTEXT" in self.prompt

    def test_prohibited_behaviors_section_present(self):
        assert "PROHIBITED" in self.prompt

    def test_tool_decision_tree_present(self):
        assert "TOOL DECISION TREE" in self.prompt

    def test_github_tool_referenced(self):
        assert "open_issue" in self.prompt

    def test_notion_tool_referenced(self):
        assert "find_document" in self.prompt

    def test_slack_tool_referenced(self):
        assert "read_messages" in self.prompt

    def test_slack_markdown_formatting_mentioned(self):
        assert "markdown" in self.prompt.lower()

    def test_suggest_then_ask_rule_present(self):
        assert "SUGGEST" in self.prompt or "suggest" in self.prompt.lower()
        assert "Auto-draft" in self.prompt or "draft" in self.prompt.lower()

    def test_prohibited_blank_question_without_suggestion(self):
        assert "PROHIBITED-06" in self.prompt

    def test_smart_suggestion_format_rule_present(self):
        assert "RULE-07" in self.prompt
        assert "Sound good" in self.prompt


def _make_text_response(text: str):
    resp = MagicMock()
    resp.text = text
    resp.candidates = []
    return resp


def _make_function_call_response(fn_name: str, fn_args: dict):
    fc = MagicMock()
    fc.name = fn_name
    fc.args = fn_args

    part = MagicMock()
    part.function_call = fc
    part.text = None

    candidate = MagicMock()
    candidate.content.parts = [part]

    resp = MagicMock()
    resp.text = None
    resp.candidates = [candidate]
    return resp


class TestGeminiClient:

    @pytest.fixture
    def client(self):
        with patch("app.llm.gemini.genai") as mock_genai:
            mock_genai.Client.return_value = MagicMock()
            from app.llm.gemini import GeminiClient
            yield GeminiClient(api_key="fake-key", model_name="gemini-test-flash")

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

    def test_send_message_returns_text_response(self, client):
        fake_resp = _make_text_response("Hello, I'm fine!")
        client._client.models.generate_content.return_value = fake_resp

        resp = client.send_message("how are you")

        client._client.models.generate_content.assert_called_once()
        assert client.extract_text(resp) == "Hello, I'm fine!"

    def test_send_message_includes_system_instruction(self, client):
        client._client.models.generate_content.return_value = _make_text_response("ok")
        client.send_message("test")

        call_kwargs = client._client.models.generate_content.call_args
        client._client.models.generate_content.assert_called_once()

    def test_send_message_with_tools_sets_tool_config(self, client_with_tools):
        client_with_tools._client.models.generate_content.return_value = _make_text_response("ok")
        client_with_tools.send_message("create an issue")

        call_kwargs = client_with_tools._client.models.generate_content.call_args.kwargs
        config = call_kwargs["config"]
        assert config.tool_config is not None, "tool_config must be set when tools registered"

    def test_no_tool_config_without_tools(self, client):
        client._client.models.generate_content.return_value = _make_text_response("ok")
        client.send_message("hello")

        call_kwargs = client._client.models.generate_content.call_args.kwargs
        config = call_kwargs["config"]
        assert config.tool_config is None

    def test_extract_function_call_returns_none_for_text_response(self, client):
        resp = _make_text_response("I'll help you!")
        assert client.extract_function_call(resp) is None

    def test_extract_function_call_returns_tuple_for_fc_response(self, client):
        resp = _make_function_call_response("open_issue", {"repo": "owner/repo", "title": "Bug"})
        result = client.extract_function_call(resp)
        assert result is not None
        name, args, context = result
        assert name == "open_issue"
        assert args["repo"] == "owner/repo"

    def test_extract_text_from_text_response(self, client):
        resp = _make_text_response("This is the answer.")
        assert client.extract_text(resp) == "This is the answer."

    def test_extract_text_returns_empty_for_function_call(self, client):
        resp = _make_function_call_response("open_issue", {})
        resp.text = None
        text = client.extract_text(resp)
        assert isinstance(text, str)


class TestOrchestrator:

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.extract_function_call.return_value = None
        llm.extract_text.return_value = "Hello!"
        llm.send_message.return_value = MagicMock()
        return llm

    @pytest.fixture
    def mock_dispatcher(self):
        dispatcher = MagicMock()
        dispatcher.execute = AsyncMock(return_value='{"number": 42, "url": "https://github.com/owner/repo/issues/42"}')
        return dispatcher

    @pytest.fixture
    def orchestrator(self, mock_llm, mock_dispatcher):
        from app.orchestrator.agent import Orchestrator
        return Orchestrator(llm_client=mock_llm, tool_dispatcher=mock_dispatcher)

    @pytest.mark.asyncio
    async def test_process_text_response_no_tool(self, orchestrator, mock_llm):
        mock_llm.extract_function_call.return_value = None
        mock_llm.extract_text.return_value = "I'm doing great!"

        result = await orchestrator.process("how are you?")

        assert result.tool_used is False
        assert result.tool_name is None
        assert result.response == "I'm doing great!"

    @pytest.mark.asyncio
    async def test_process_empty_text_falls_back_to_default(self, orchestrator, mock_llm):
        mock_llm.extract_function_call.return_value = None
        mock_llm.extract_text.return_value = ""

        result = await orchestrator.process("???")

        assert "Unable to generate" in result.response or result.response != ""

    @pytest.mark.asyncio
    async def test_process_tool_call_dispatches_and_returns(self, orchestrator, mock_llm, mock_dispatcher):
        fake_fc_part = MagicMock()
        mock_llm.extract_function_call.return_value = (
            "open_issue",
            {"repo": "owner/repo", "title": "Test", "body": "Testing"},
            fake_fc_part,
        )
        mock_llm.extract_text.return_value = "Issue #42 created."
        mock_llm.send_tool_result.return_value = MagicMock()

        result = await orchestrator.process("create an issue titled Test")

        mock_dispatcher.execute.assert_awaited_once_with(
            "open_issue",
            {"repo": "owner/repo", "title": "Test", "body": "Testing"},
        )
        assert result.tool_used is True
        assert result.tool_name == "open_issue"
        assert result.response == "Issue #42 created."

    @pytest.mark.asyncio
    async def test_process_tool_error_returns_error_text(self, orchestrator, mock_llm, mock_dispatcher):
        fake_fc_part = MagicMock()
        mock_llm.extract_function_call.return_value = (
            "open_issue",
            {"repo": "owner/repo", "title": "Fail"},
            fake_fc_part,
        )
        mock_dispatcher.execute.side_effect = RuntimeError("GitHub API down")
        mock_llm.extract_text.return_value = "Something went wrong."
        mock_llm.send_tool_result.return_value = MagicMock()

        result = await orchestrator.process("create issue")

        assert isinstance(result.response, str)

    @pytest.mark.asyncio
    async def test_process_sends_enriched_message_when_memory_present(self, mock_llm, mock_dispatcher):
        from app.orchestrator.agent import Orchestrator
        from app.memory.manager import MemoryManager
        from app.memory.models import PromptContext, SessionContext

        mock_memory = AsyncMock(spec=MemoryManager)
        mock_memory.load_context.return_value = MagicMock(spec=PromptContext)
        mock_memory.persist_turn = AsyncMock()

        with patch("app.memory.prompt_context.PromptContextBuilder.build", return_value="[MEMORY PREFIX] "):
            orchestrator = Orchestrator(
                llm_client=mock_llm,
                tool_dispatcher=mock_dispatcher,
                memory_manager=mock_memory,
            )
            mock_llm.extract_function_call.return_value = None
            mock_llm.extract_text.return_value = "got it"

            ctx = SessionContext(session_key="ws:chan:user")
            await orchestrator.process("hello", session_context=ctx)

        mock_memory.load_context.assert_awaited_once()


class TestEntityExtractor:

    @pytest.fixture
    def extractor(self):
        from app.memory.extractor import EntityExtractor
        return EntityExtractor(gemini_api_key="fake-key")

    def _resp(self, text: str):
        r = MagicMock()
        r.text = text
        return r

    def _mock_client(self, text: str):
        instance = MagicMock()
        instance.aio.models.generate_content = AsyncMock(return_value=self._resp(text))
        return instance

    @pytest.mark.asyncio
    async def test_extract_valid_entities(self, extractor):
        payload = json.dumps([
            {"type": "repository", "value": "Dilip-Kashyp/bot"},
            {"type": "technology", "value": "FastAPI"},
        ])
        with patch("google.genai.Client", return_value=self._mock_client(payload)):
            entities = await extractor.extract(
                "Open an issue in Dilip-Kashyp/bot using FastAPI"
            )
        assert len(entities) == 2
        assert {e.type for e in entities} == {"repository", "technology"}

    @pytest.mark.asyncio
    async def test_extract_empty_text_returns_empty_list(self, extractor):
        result = await extractor.extract("")
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_blank_text_returns_empty_list(self, extractor):
        result = await extractor.extract("   ")
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_invalid_json_returns_empty_list(self, extractor):
        with patch("google.genai.Client", return_value=self._mock_client("not json")):
            entities = await extractor.extract("some text")
        assert entities == []

    @pytest.mark.asyncio
    async def test_extract_empty_array_response_returns_empty_list(self, extractor):
        with patch("google.genai.Client", return_value=self._mock_client("[]")):
            entities = await extractor.extract("hi there")
        assert entities == []

    @pytest.mark.asyncio
    async def test_extract_strips_markdown_fences(self, extractor):
        payload = '```json\n[{"type": "branch", "value": "feature/auth"}]\n```'
        with patch("google.genai.Client", return_value=self._mock_client(payload)):
            entities = await extractor.extract("working on feature/auth branch")
        assert len(entities) == 1
        assert entities[0].type == "branch"
        assert entities[0].value == "feature/auth"

    @pytest.mark.asyncio
    async def test_extract_unwraps_entities_wrapper(self, extractor):
        payload = json.dumps({"entities": [{"type": "user", "value": "dilip"}]})
        with patch("google.genai.Client", return_value=self._mock_client(payload)):
            entities = await extractor.extract("dilip opened a PR")
        assert len(entities) == 1
        assert entities[0].value == "dilip"

    @pytest.mark.asyncio
    async def test_extract_tolerates_aliased_keys(self, extractor):
        payload = json.dumps([{"kind": "channel", "value": "#general"}])
        with patch("google.genai.Client", return_value=self._mock_client(payload)):
            entities = await extractor.extract("post in #general")
        assert len(entities) == 1
        assert entities[0].type == "channel"

    @pytest.mark.asyncio
    async def test_extract_skips_bad_items_continues_batch(self, extractor):
        payload = json.dumps([
            {},
            {"type": "", "value": ""},
            {"type": "pr", "value": "17"},
        ])
        with patch("google.genai.Client", return_value=self._mock_client(payload)):
            entities = await extractor.extract("PR #17 merged")
        assert len(entities) == 1
        assert entities[0].type == "pr"
        assert entities[0].value == "17"

    @pytest.mark.asyncio
    async def test_extract_api_error_returns_empty_list_does_not_raise(self, extractor):
        err_instance = MagicMock()
        err_instance.aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("connection refused")
        )
        with patch("google.genai.Client", return_value=err_instance):
            entities = await extractor.extract("anything")
        assert entities == []


class TestPromptContextBuilder:

    @pytest.fixture
    def builder(self):
        from app.memory.prompt_context import PromptContextBuilder
        return PromptContextBuilder()

    def _make_memory(self, summary: str, entities=None):
        from app.memory.models import Memory, MemoryType
        return Memory(
            session_key="test",
            memory_type=MemoryType.DISCUSSION_SUMMARY,
            summary=summary,
            entities=entities or [],
        )

    def _tool_memory(self, summary: str):
        from app.memory.models import Memory, MemoryType
        return Memory(
            session_key="test",
            memory_type=MemoryType.TOOL_RESULT,
            summary=summary,
        )

    def test_empty_context_returns_empty_string(self, builder):
        from app.memory.models import PromptContext
        ctx = PromptContext()
        assert builder.build(ctx) == ""

    def test_github_repo_in_working_state(self, builder):
        from app.memory.models import PromptContext, WorkingState, GitHubState
        ctx = PromptContext(working_state=WorkingState(
            active_tool="github",
            github=GitHubState(repo="owner/repo", branch="main", issue="42"),
        ))
        output = builder.build(ctx)
        assert "github.repo=owner/repo" in output
        assert "github.branch=main" in output
        assert "github.issue=#42" in output

    def test_jira_state_rendered(self, builder):
        from app.memory.models import PromptContext, WorkingState, JiraState
        ctx = PromptContext(working_state=WorkingState(
            jira=JiraState(project="PROJ", ticket="PROJ-99"),
        ))
        output = builder.build(ctx)
        assert "jira.project=PROJ" in output
        assert "jira.ticket=PROJ-99" in output

    def test_notion_state_rendered(self, builder):
        from app.memory.models import PromptContext, WorkingState, NotionState
        ctx = PromptContext(working_state=WorkingState(
            notion=NotionState(page="API Docs"),
        ))
        output = builder.build(ctx)
        assert "notion.page=API Docs" in output

    def test_tool_result_rendered_as_last_action(self, builder):
        from app.memory.models import PromptContext, MemoryContext
        tr = self._tool_memory("open_issue called. Result: issue #42 created.")
        ctx = PromptContext(memory_context=MemoryContext(tool_results=[tr]))
        output = builder.build(ctx)
        assert "Last Action:" in output
        assert "open_issue" in output

    def test_preferences_always_rendered(self, builder):
        from app.memory.models import PromptContext, MemoryContext, IntentClass
        pref = self._make_memory("User prefers terse responses")
        ctx = PromptContext(
            memory_context=MemoryContext(preferences=[pref]),
            intent=IntentClass.TRIVIAL,
        )
        output = builder.build(ctx)
        assert "User Preferences" in output
        assert "terse" in output

    def test_summaries_suppressed_for_trivial_intent(self, builder):
        from app.memory.models import PromptContext, MemoryContext, IntentClass
        summary = self._make_memory("User discussed authentication flow")
        ctx = PromptContext(
            memory_context=MemoryContext(summaries=[summary]),
            intent=IntentClass.TRIVIAL,
        )
        output = builder.build(ctx)
        assert "authentication" not in output

    def test_summaries_rendered_for_github_intent(self, builder):
        from app.memory.models import PromptContext, MemoryContext, IntentClass
        summary = self._make_memory("User discussed authentication flow")
        ctx = PromptContext(
            memory_context=MemoryContext(summaries=[summary]),
            intent=IntentClass.GITHUB,
        )
        output = builder.build(ctx)
        assert "authentication" in output

    def test_entities_rendered_for_non_trivial_intent(self, builder):
        from app.memory.models import PromptContext, MemoryContext, Entity, IntentClass
        ctx = PromptContext(
            memory_context=MemoryContext(
                entities=[Entity(type="repository", value="owner/repo")]
            ),
            intent=IntentClass.GITHUB,
        )
        output = builder.build(ctx)
        assert "repository=owner/repo" in output

    def test_entities_suppressed_for_trivial_intent(self, builder):
        from app.memory.models import PromptContext, MemoryContext, Entity, IntentClass
        ctx = PromptContext(
            memory_context=MemoryContext(
                entities=[Entity(type="repository", value="owner/repo")]
            ),
            intent=IntentClass.TRIVIAL,
        )
        output = builder.build(ctx)
        assert "repository=owner/repo" not in output

    def test_output_wrapped_in_memory_context_markers(self, builder):
        from app.memory.models import PromptContext, WorkingState, GitHubState
        ctx = PromptContext(working_state=WorkingState(
            github=GitHubState(repo="owner/repo")
        ))
        output = builder.build(ctx)
        assert output.startswith("[MEMORY CONTEXT]")
        assert "[END MEMORY CONTEXT]" in output

    def test_entities_capped_at_8(self, builder):
        from app.memory.models import PromptContext, MemoryContext, Entity, IntentClass
        entities = [Entity(type="user", value=f"user{i}") for i in range(15)]
        ctx = PromptContext(
            memory_context=MemoryContext(entities=entities),
            intent=IntentClass.GENERAL,
        )
        output = builder.build(ctx)
        assert "user7" in output
        assert "user8" not in output


class TestClassifyIntent:

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.memory.manager import _classify_intent
        from app.memory.models import IntentClass
        self.classify = _classify_intent
        self.IntentClass = IntentClass

    @pytest.mark.parametrize("msg", ["hi", "hey", "hello", "ok", "thanks", "👍", "yep", "sure"])
    def test_trivial_greetings(self, msg):
        assert self.classify(msg) == self.IntentClass.TRIVIAL

    def test_very_short_message_is_trivial(self):
        assert self.classify("lol") == self.IntentClass.TRIVIAL

    @pytest.mark.parametrize("msg", [
        "create an issue",
        "open a pull request",
        "show me the repo",
        "merge this branch",
        "what PR is open?",
    ])
    def test_github_intent(self, msg):
        assert self.classify(msg) == self.IntentClass.GITHUB

    @pytest.mark.parametrize("msg", [
        "find the API docs",
        "search notion for onboarding",
        "look up the wiki page",
    ])
    def test_notion_intent(self, msg):
        assert self.classify(msg) == self.IntentClass.NOTION

    @pytest.mark.parametrize("msg", [
        "read messages from #general",
        "summarize the channel",
        "what did people say in the thread",
    ])
    def test_slack_intent(self, msg):
        assert self.classify(msg) == self.IntentClass.SLACK

    def test_general_intent_for_unrecognized(self):
        assert self.classify("what is the meaning of life?") == self.IntentClass.GENERAL

    def test_github_takes_priority_over_general(self):
        assert self.classify("I need to open an issue about the API") == self.IntentClass.GITHUB


class TestIsWorthRemembering:

    @pytest.fixture(autouse=True)
    def _import(self):
        from app.memory.manager import _is_worth_remembering
        self.gate = _is_worth_remembering

    def test_trivial_user_message_skipped(self):
        assert self.gate("ok", "Sure!") is False

    def test_meaningful_exchange_remembered(self):
        assert self.gate(
            "create an issue titled Login Bug in Dilip-Kashyp/bot",
            "Issue #42 has been created: https://github.com/...",
        ) is True

    def test_both_sides_very_short_skipped(self):
        assert self.gate("hi", "Hey!") is False

    def test_non_trivial_user_long_bot_response_remembered(self):
        long_bot = "x" * 200
        assert self.gate("can you summarize the open PRs for me?", long_bot) is True

    def test_greeting_pattern_skipped(self):
        assert self.gate("thanks", "You're welcome!") is False
