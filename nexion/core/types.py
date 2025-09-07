from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum


class Channel(str, Enum):
    HTTP = "http"
    TELEGRAM = "telegram"


@dataclass
class MessageEvent:
    channel: Channel
    user_id: str
    text: str
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
