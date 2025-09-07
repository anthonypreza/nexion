from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    @abstractmethod
    async def chat(self, model: str, messages: list[dict[str, Any]]) -> str:
        raise NotImplementedError("Must be implemented by subclass")
