from dataclasses import dataclass
from enum import Enum
from typing import Any


class Channel(str, Enum):
    HTTP = "http"
    TELEGRAM = "telegram"
    DISCORD = "discord"


@dataclass
class MessageEvent:
    channel: Channel
    user_id: str
    text: str
    bot_id: str
    workspace_id: str = "default"
    thread_id: str | None = None
    chat_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class Reply:
    text: str
    metadata: dict[str, Any] | None = None


@dataclass
class ProviderMessage:
    role: str
    content: str | list[dict[str, Any]]  # Support structured content for tool calls
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None

    def serialize(self) -> dict[str, Any]:
        base = {"role": self.role, "content": self.content}
        if self.tool_calls:
            base["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            base["tool_call_id"] = self.tool_call_id
        return base


@dataclass
class ConversationContext:
    """Context for a conversation including history and state."""

    conversation_id: str
    workspace_id: str
    bot_id: str
    channel_ref: str
    chat_ref: str  # Chat ID where conversation takes place
    thread_id: str | None = None
    state: dict[str, Any] | None = None
    history: list[ProviderMessage] | None = None


@dataclass
class ToolCall:
    """Structured tool call information."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    """Chat response with tool calls."""

    content: str
    tool_calls: list[ToolCall] | None = None
