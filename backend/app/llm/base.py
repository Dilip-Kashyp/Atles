import abc
from typing import Any


class LLMClient(abc.ABC):
    @abc.abstractmethod
    async def send_message(self, user_message: str) -> Any:
        pass

    @abc.abstractmethod
    async def send_tool_result(self, original_message: str, tool_call_context: Any, tool_result: str) -> Any:
        pass

    @abc.abstractmethod
    def extract_function_call(self, response: Any) -> tuple[str, dict[str, Any], Any] | None:
        pass

    @abc.abstractmethod
    def extract_text(self, response: Any) -> str:
        pass
