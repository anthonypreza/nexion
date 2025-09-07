import json

import httpx

from ..core.types import ChatResponse, ProviderMessage, ToolCall
from ..tools.base import ToolSchema
from ..utils.logging import get_logger
from .base import Provider


class OpenAIProvider(Provider):
    BASE_URL = "https://api.openai.com"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.logger = get_logger("openai")

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
            "input": [self._serialize_message_for_responses(m) for m in messages],
            "max_output_tokens": self.max_tokens,
        }

        if system_prompt:
            payload["instructions"] = system_prompt

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            if res.is_error:
                raise httpx.HTTPStatusError(
                    f"OpenAI error {res.status_code}: {res.text}",
                    request=res.request,
                    response=res,
                )
            resp_json = res.json()

            # Handle both GPT-4 and GPT-5 response formats
            try:
                # Try GPT-5 format first (newer format)
                if "output" in resp_json and len(resp_json["output"]) > 0:
                    # Look for message type in output array
                    for output_item in resp_json["output"]:
                        if (
                            output_item.get("type") == "message"
                            and "content" in output_item
                        ):
                            content = output_item["content"]
                            if len(content) > 0 and "text" in content[0]:
                                return content[0]["text"]

                # Fallback to GPT-4 format (legacy format)
                if "output" in resp_json and len(resp_json["output"]) > 0:
                    first_output = resp_json["output"][0]
                    if "content" in first_output and len(first_output["content"]) > 0:
                        return first_output["content"][0]["text"]

                # If neither format works, raise an error
                raise ValueError("Unexpected response format from OpenAI API")

            except (KeyError, IndexError, TypeError) as e:
                raise ValueError(
                    f"Failed to parse OpenAI response: {e}. Response: {resp_json}"
                ) from e

    async def chat_with_tools(
        self,
        model: str,
        messages: list[ProviderMessage],
        system_prompt: str | None = None,
        tools: list[ToolSchema] = None,
    ) -> ChatResponse:
        url = f"{OpenAIProvider.BASE_URL}/v1/responses"

        # Build payload with tools
        payload = {
            "model": model,
            "input": [self._serialize_message_for_responses(m) for m in messages],
            "max_output_tokens": self.max_tokens,
        }
        # Log minimal request details for debugging
        # Lightweight debug log (counts only; no payloads)
        self.logger.debug(
            f"OpenAI request: messages={len(messages)} tools={len(tools) if tools else 0}"
        )

        if system_prompt:
            payload["instructions"] = system_prompt

        if tools:
            # Convert ToolSchema to OpenAI Responses API tool format
            # Required fields: type=function, name, parameters (JSON schema). Description optional.
            payload["tools"] = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in tools
            ]
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=self._get_headers(), json=payload)
            if res.is_error:
                raise httpx.HTTPStatusError(
                    f"OpenAI error {res.status_code}: {res.text}",
                    request=res.request,
                    response=res,
                )
            resp_json = res.json()

            try:
                # Parse response for tool calls
                tool_calls = []
                content = ""

                # Handle GPT-5 format
                if "output" in resp_json and len(resp_json["output"]) > 0:
                    for output_item in resp_json["output"]:
                        if output_item.get("type") == "message":
                            if (
                                "content" in output_item
                                and len(output_item["content"]) > 0
                            ):
                                content = output_item["content"][0].get("text", "")

                        elif output_item.get("type") == "function_call":
                            raw_args = output_item.get("arguments", {})
                            # Normalize arguments to a dict
                            if isinstance(raw_args, str):
                                try:
                                    parsed_args = json.loads(raw_args)
                                except Exception:
                                    parsed_args = {}
                            elif isinstance(raw_args, list):
                                # Some Responses variants return a list of {name, value}
                                parsed_args = {}
                                for item in raw_args:
                                    if isinstance(item, dict) and "name" in item:
                                        parsed_args[item["name"]] = item.get("value")
                            elif isinstance(raw_args, dict):
                                parsed_args = raw_args
                            else:
                                parsed_args = {}
                            tool_calls.append(
                                ToolCall(
                                    id=output_item.get("call_id", ""),
                                    name=output_item.get("name", ""),
                                    arguments=parsed_args,
                                )
                            )

                # Fallback to GPT-4 format if no GPT-5 format found
                if not content and not tool_calls and "output" in resp_json:
                    first_output = resp_json["output"][0] if resp_json["output"] else {}
                    if "content" in first_output and len(first_output["content"]) > 0:
                        content = first_output["content"][0].get("text", "")

                return ChatResponse(
                    content=content, tool_calls=tool_calls if tool_calls else None
                )

            except (KeyError, IndexError, TypeError) as e:
                raise ValueError(
                    f"Failed to parse OpenAI response: {e}. Response: {resp_json}"
                ) from e

    @staticmethod
    def _serialize_message_for_responses(message: ProviderMessage) -> dict:
        """Convert ProviderMessage to Responses API message format.

        - Filters unsupported roles (e.g., maps 'tool' to 'user' with plain text content).
        - Converts simple string content into the array-of-blocks format expected by Responses.
        """
        role = message.role
        content = message.content

        # Determine Responses content type based on role
        # assistant -> 'output_text'; others -> 'input_text'
        def _block(block_text: str, r: str) -> dict:
            t = "output_text" if r == "assistant" else "input_text"
            return {"type": t, "text": block_text}

        # Map unsupported 'tool' role to 'user' carrying result as text
        if role == "tool":
            role = "user"
            prefix = "Tool result"
            if message.tool_call_id:
                prefix += f" (tool_call_id={message.tool_call_id})"
            content_text = (
                f"{prefix}: {content}"
                if isinstance(content, str)
                else f"{prefix}: {json.dumps(content)}"
            )
            return {"role": role, "content": [_block(content_text, role)]}

        # Convert plain string to block format
        if isinstance(content, str):
            return {"role": role, "content": [_block(content, role)]}

        # If content is structured (e.g., Anthropic-style blocks), coerce to text blocks
        if isinstance(content, list):
            blocks = []
            for b in content:
                if not isinstance(b, dict):
                    blocks.append(_block(str(b), role))
                    continue
                btype = b.get("type")
                if btype == "text" and "text" in b:
                    blocks.append(_block(b["text"], role))
                elif btype == "tool_result":
                    text = f"Tool result ({b.get('tool_use_id', '')}): {b.get('content', '')}"
                    blocks.append(_block(text, role))
                elif btype == "tool_use":
                    text = f"Tool call {b.get('name', '')} args: {json.dumps(b.get('input', {}))}"
                    blocks.append(_block(text, role))
                else:
                    blocks.append(_block(json.dumps(b), role))
            return {"role": role, "content": blocks}

        # Last resort: stringify
        return {"role": role, "content": [_block(str(content), role)]}
