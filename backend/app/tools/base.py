import abc
from typing import Any


class BaseTool(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def input_schema(self) -> dict[str, Any]:
        pass

    @abc.abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> str:
        pass
