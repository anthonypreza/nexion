import httpx

from ..core.types import ChatResponse, ProviderMessage, ToolCall
from ..tools.base import ToolSchema
from ..utils.logging import get_logger
from .base import Provider


class AnthropicProvider(Provider):
    BASE_URL = "https://api.anthropic.com"

    def __init__(self, *args, anthropic_version: str = "2023-06-01", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.anthropic_version = anthropic_version
        self.logger = get_logger("anthropic")

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
        self.logger.debug(f"Anthropic request: messages={len(messages)} tools=0")

        # Add system prompt as top-level parameter if provided
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            if res.is_error:
                # Surface server-provided error details to aid debugging
                raise httpx.HTTPStatusError(
                    f"Anthropic error {res.status_code}: {res.text}",
                    request=res.request,
                    response=res,
                )
            resp_json = res.json()

            return resp_json["content"][0]["text"]

    async def chat_with_tools(
        self,
        model: str,
        messages: list[ProviderMessage],
        system_prompt: str | None = None,
        tools: list[ToolSchema] = None,
    ) -> ChatResponse:
        url = f"{AnthropicProvider.BASE_URL}/v1/messages"

        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [message.serialize() for message in messages],
        }

        # Add system prompt as top-level parameter if provided
        if system_prompt:
            payload["system"] = system_prompt

        # Add tools in Anthropic format
        if tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in tools
            ]
        self.logger.debug(
            f"Anthropic request (tools): messages={len(messages)} tools={len(tools) if tools else 0}"
        )

        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            if res.is_error:
                # Provide detailed error body for easier diagnosis (e.g., schema issues)
                raise httpx.HTTPStatusError(
                    f"Anthropic error {res.status_code}: {res.text}",
                    request=res.request,
                    response=res,
                )
            resp_json = res.json()

            try:
                # Parse Anthropic response format
                content = ""
                tool_calls = []

                for content_block in resp_json.get("content", []):
                    if content_block.get("type") == "text":
                        content += content_block.get("text", "")
                    elif content_block.get("type") == "tool_use":
                        tool_calls.append(
                            ToolCall(
                                id=content_block.get("id", ""),
                                name=content_block.get("name", ""),
                                arguments=content_block.get("input", {}),
                            )
                        )

                return ChatResponse(
                    content=content, tool_calls=tool_calls if tool_calls else None
                )

            except (KeyError, IndexError, TypeError) as e:
                raise ValueError(
                    f"Failed to parse Anthropic response: {e}. Response: {resp_json}"
                ) from e
