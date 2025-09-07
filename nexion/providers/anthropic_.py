import httpx
from typing import List, Dict

from .provider import Provider
from ..core.types import ProviderMessage


class AnthropicProvider(Provider):
    BASE_URL = "https://api.anthropic.com"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def chat(self, model: str, messages: List[ProviderMessage]) -> str:
        url = f"{AnthropicProvider.BASE_URL}/v1/messages"
        payload = {"model": model, "max_tokens": 1000, "messages": messages}

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            res.raise_for_status()
            json = res.json()
            return json["content"][0]["text"]
