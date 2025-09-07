import httpx

from ..core.types import ProviderMessage
from .base import Provider


class OpenAIProvider(Provider):
    BASE_URL = "https://api.openai.com"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _get_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    async def chat(
        self,
        model: str,
        messages: list[ProviderMessage],
        system_prompt: str | None = None,
    ) -> str:
        url = f"{OpenAIProvider.BASE_URL}/v1/responses"

        # Build payload with instructions field for system prompt
        payload = {
            "model": model,
            "input": [message.serialize() for message in messages],
            "max_output_tokens": self.max_tokens,
        }

        if system_prompt:
            payload["instructions"] = system_prompt

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            res.raise_for_status()
            json = res.json()

            # Handle both GPT-4 and GPT-5 response formats
            try:
                # Try GPT-5 format first (newer format)
                if "output" in json and len(json["output"]) > 0:
                    # Look for message type in output array
                    for output_item in json["output"]:
                        if (
                            output_item.get("type") == "message"
                            and "content" in output_item
                        ):
                            content = output_item["content"]
                            if len(content) > 0 and "text" in content[0]:
                                return content[0]["text"]

                # Fallback to GPT-4 format (legacy format)
                if "output" in json and len(json["output"]) > 0:
                    first_output = json["output"][0]
                    if "content" in first_output and len(first_output["content"]) > 0:
                        return first_output["content"][0]["text"]

                # If neither format works, raise an error
                raise ValueError("Unexpected response format from OpenAI API")

            except (KeyError, IndexError, TypeError) as e:
                raise ValueError(
                    f"Failed to parse OpenAI response: {e}. Response: {json}"
                ) from e
