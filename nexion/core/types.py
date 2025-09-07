from dataclasses import dataclass
from enum import Enum
from typing import Any


class Channel(str, Enum):
    HTTP = "http"
    TELEGRAM = "telegram"


@dataclass
class MessageEvent:
    channel: Channel
    user_id: str
    text: str
    bot_id: str
    workspace_id: str = "default"
    thread_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class Reply:
    text: str
    metadata: dict[str, Any] | None = None


@dataclass
class ProviderMessage:
    role: str
    content: str


@dataclass
class ConversationContext:
    """Context for a conversation including history and state."""

    conversation_id: str
    workspace_id: str
    bot_id: str
    channel_ref: str
    user_ref: str
    thread_id: str | None = None
    state: dict[str, Any] | None = None
    history: list[ProviderMessage] | None = None
