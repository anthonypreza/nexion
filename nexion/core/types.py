from dataclasses import dataclass
from typing import Any, Dict, Optional, List
from enum import Enum


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
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Reply:
    text: str
    metadata: Optional[Dict[str, Any]] = None


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
    thread_id: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    history: Optional[List[ProviderMessage]] = None
