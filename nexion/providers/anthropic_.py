import httpx

from ..core.types import ProviderMessage
from .base import Provider


class AnthropicProvider(Provider):
    BASE_URL = "https://api.anthropic.com"

    def __init__(self, *args, anthropic_version: str = "2023-06-01", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.anthropic_version = anthropic_version

    def _get_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        model: str,
        messages: list[ProviderMessage],
        system_prompt: str | None = None,
    ) -> str:
        url = f"{AnthropicProvider.BASE_URL}/v1/messages"

        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [message.serialize() for message in messages],
        }

        # Add system prompt as top-level parameter if provided
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            res.raise_for_status()
            json = res.json()

            return json["content"][0]["text"]
