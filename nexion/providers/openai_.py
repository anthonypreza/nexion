import httpx
from typing import List, Dict

from .base import Provider
from ..core.types import ProviderMessage


class OpenAIProvider(Provider):
    BASE_URL = "https://api.openai.com"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    async def chat(self, model: str, messages: List[ProviderMessage]) -> str:
        url = f"{OpenAIProvider.BASE_URL}/v1/responses"
        payload = {"model": model, "input": messages}

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            res.raise_for_status()
            json = res.json()
            return json["output"][0]["content"][0]["text"]
