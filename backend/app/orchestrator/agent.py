import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.llm.base import LLMClient
from app.orchestrator.tool_dispatcher import ToolDispatcher

if TYPE_CHECKING:
    from app.memory.manager import MemoryManager
    from app.memory.models import SessionContext

log = logging.getLogger(__name__)


@dataclass
class OrchestratorResult:
    response: str
    tool_used: bool
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None


class Orchestrator:
    def __init__(
        self,
        llm_client: LLMClient,
        tool_dispatcher: ToolDispatcher,
        memory_manager: "MemoryManager | None" = None,
    ) -> None:
        self._llm    = llm_client
        self._tools  = tool_dispatcher
        self._memory = memory_manager

    async def process(
        self,
        user_message: str,
        session_context: "SessionContext | None" = None,
    ) -> OrchestratorResult:
        log.info("[CHECKPOINT 1/4: ORCHESTRATOR_START] Query: %r", user_message[:80])

        # ── Memory: load context and build enriched prompt ─────────────────────
        enriched_message = user_message
        if self._memory is not None and session_context is not None:
            from app.memory.prompt_context import PromptContextBuilder
            prompt_ctx = await self._memory.load_context(
                session_context, user_message=user_message
            )
            prefix = PromptContextBuilder().build(prompt_ctx)
            if prefix:
                enriched_message = prefix + user_message
                log.info("[CHECKPOINT: MEMORY_CONTEXT_INJECTED] Prefix=%d chars", len(prefix))


        # ── LLM: first call ────────────────────────────────────────────────────
        log.info("[CHECKPOINT 2/4: LLM_QUERY] Sending prompt to LLM")
        first_response = self._llm.send_message(enriched_message)
        function_call  = self._llm.extract_function_call(first_response)

        if function_call is not None:
            tool_name, tool_args, tool_context = function_call
            log.info("[CHECKPOINT 3/4: TOOL_DISPATCH] LLM requested tool '%s'", tool_name)

            try:
                tool_result = await self._tools.execute(tool_name, tool_args)
            except Exception as e:
                log.exception("[CHECKPOINT: TOOL_ERROR] Execution failed for '%s'", tool_name)
                tool_result = f"Error executing tool {tool_name}: {e}"
            else:
                # ── Memory: update working state after successful tool call ────
                if self._memory is not None and session_context is not None:
                    await self._memory.on_tool_success(
                        session_key=session_context.session_key,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        tool_result=tool_result,
                    )

            log.info("[CHECKPOINT: TOOL_SUCCESS] Feeding result back to LLM")
            final_response = self._llm.send_tool_result(
                original_message=enriched_message,
                tool_call_context=tool_context,
                tool_result=tool_result,
            )

            final_text = self._llm.extract_text(final_response)
            if not final_text:
                final_text = "Retrieved tool data, but generated no text. Raw result:\n\n" + tool_result

            # ── Memory: persist the completed turn ────────────────────────────
            if self._memory is not None and session_context is not None:
                await self._memory.persist_turn(
                    session_key=session_context.session_key,
                    user_message=user_message,
                    assistant_response=final_text,
                )

            log.info("[CHECKPOINT 4/4: ORCHESTRATOR_COMPLETE] Processed with tool '%s'", tool_name)
            return OrchestratorResult(
                response=final_text,
                tool_used=True,
                tool_name=tool_name,
                tool_arguments=tool_args,
            )

        else:
            direct_text = self._llm.extract_text(first_response)
            if not direct_text:
                direct_text = "Unable to generate a response. Please try rephrasing."

            # ── Memory: persist the completed turn ────────────────────────────
            if self._memory is not None and session_context is not None:
                await self._memory.persist_turn(
                    session_key=session_context.session_key,
                    user_message=user_message,
                    assistant_response=direct_text,
                )

            log.info("[CHECKPOINT 4/4: ORCHESTRATOR_COMPLETE] Processed without tools")
            return OrchestratorResult(
                response=direct_text,
                tool_used=False,
            )
