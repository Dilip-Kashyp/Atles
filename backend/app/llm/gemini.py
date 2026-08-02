import json
import logging
from typing import Any

from google import genai
from google.genai import types

from app.llm.base import LLMClient
from app.llm.prompts import SYSTEM_INSTRUCTION
from app.tools.base import BaseTool

log = logging.getLogger(__name__)


def tool_to_gemini_declaration(tool: BaseTool) -> types.FunctionDeclaration:
    schema = tool.input_schema
    if "type" not in schema:
        schema = {"type": "object", "properties": schema}

    return types.FunctionDeclaration(
        name=tool.name,
        description=tool.description or f"Execute the {tool.name} tool.",
        parameters=schema,
    )


class GeminiClient(LLMClient):
    _SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION

    def __init__(
        self,
        api_key: str,
        model_name: str,
        tools: list[BaseTool] | None = None,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._gemini_tools: list[types.Tool] | None = None

        if tools:
            declarations = [tool_to_gemini_declaration(t) for t in tools]
            self._gemini_tools = [types.Tool(function_declarations=declarations)]
            log.info("[CHECKPOINT: LLM_INIT] Registered %d tool(s): %s", len(declarations), [d.name for d in declarations])

    def send_message(self, user_message: str) -> types.GenerateContentResponse:
        log.info("[CHECKPOINT: LLM_SEND_MESSAGE] Prompting Gemini (%d chars)", len(user_message))
        # SDK-level tool enforcement (Fix 3):
        #   mode="AUTO" → Gemini evaluates all function declarations on every
        #   call and calls one when it applies.  Combined with the strict
        #   RULE-01/PROHIBITED-01 prompt rules this creates a two-layer
        #   guarantee against the LLM ignoring tools.
        tool_config = (
            types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="AUTO")
            )
            if self._gemini_tools
            else None
        )
        config = types.GenerateContentConfig(
            system_instruction=self._SYSTEM_INSTRUCTION,
            tools=self._gemini_tools,
            tool_config=tool_config,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=user_message,
            config=config,
        )
        self._log_response(response)
        return response

    def send_tool_result(
        self,
        original_message: str,
        tool_call_context: Any,
        tool_result: str,
    ) -> types.GenerateContentResponse:
        try:
            structured_result: Any = json.loads(tool_result)
        except (json.JSONDecodeError, ValueError):
            structured_result = {"result": tool_result}

        function_call_part = tool_call_context
        fn_name = function_call_part.function_call.name
        log.info("[CHECKPOINT: LLM_FEED_TOOL_RESULT] Sending '%s' result back to Gemini", fn_name)

        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=original_message)]),
            types.Content(role="model", parts=[function_call_part]),
            types.Content(
                role="user",
                parts=[types.Part.from_function_response(name=fn_name, response={"result": structured_result})],
            ),
        ]

        # Same tool_config as send_message — enforce AUTO mode on follow-up calls too
        tool_config = (
            types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="AUTO")
            )
            if self._gemini_tools
            else None
        )
        config = types.GenerateContentConfig(
            system_instruction=self._SYSTEM_INSTRUCTION,
            tools=self._gemini_tools,
            tool_config=tool_config,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        response = self._client.models.generate_content(
            model=self._model_name,
            contents=contents,
            config=config,
        )
        self._log_response(response)
        return response

    @staticmethod
    def extract_function_call_part(response: types.GenerateContentResponse) -> types.Part | None:
        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                if part.function_call and part.function_call.name:
                    return part
        return None

    def extract_function_call(self, response: types.GenerateContentResponse) -> tuple[str, dict[str, Any], Any] | None:
        fc_part = self.extract_function_call_part(response)
        if fc_part and fc_part.function_call:
            return fc_part.function_call.name, dict(fc_part.function_call.args), fc_part
        return None

    @staticmethod
    def extract_text(response: types.GenerateContentResponse) -> str:
        try:
            if response.text:
                return response.text
        except (AttributeError, ValueError):
            pass

        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                if hasattr(part, "text") and part.text:
                    return part.text
        return ""

    @staticmethod
    def _log_response(response: types.GenerateContentResponse) -> None:
        fc_part = GeminiClient.extract_function_call_part(response)
        if fc_part:
            log.info("[CHECKPOINT: LLM_RESPONSE] Requested function_call: %s", fc_part.function_call.name)
        else:
            text = GeminiClient.extract_text(response)
            log.info("[CHECKPOINT: LLM_RESPONSE] Text generated (%d chars)", len(text))
