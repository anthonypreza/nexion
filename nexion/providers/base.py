from abc import ABC, abstractmethod

from ..core.types import ProviderMessage


class Provider(ABC):
    def __init__(self, api_key: str | None = None, max_tokens: int | None = 1024):
        self.api_key = api_key
        self.max_tokens = max_tokens

    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: list[ProviderMessage],
        system_prompt: str | None = None,
    ) -> str:
        raise NotImplementedError("Must be implemented by subclass")
