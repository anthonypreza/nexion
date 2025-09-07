from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import uuid4

from .models import Conversation, Message


class ConversationStore(ABC):
    """Abstract base class for conversation storage implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend (create tables, etc.)."""
        pass

    @abstractmethod
    async def get_or_create_conversation(
        self,
        workspace_id: str,
        bot_id: str,
        channel_ref: str,
        user_ref: str,
        thread_id: Optional[str] = None,
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        pass

    @abstractmethod
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Add a message to a conversation."""
        pass

    @abstractmethod
    async def get_conversation_history(
        self, conversation_id: str, limit: int = 10
    ) -> List[Message]:
        """Get recent messages for a conversation, ordered by created_at DESC."""
        pass

    @abstractmethod
    async def update_conversation_state(
        self, conversation_id: str, state: Dict[str, Any]
    ) -> None:
        """Update conversation state/metadata."""
        pass

    @abstractmethod
    async def get_conversation_by_id(
        self, conversation_id: str
    ) -> Optional[Conversation]:
        """Get conversation by ID."""
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        pass

    # Helper methods

    def generate_conversation_id(self) -> str:
        """Generate a unique conversation ID."""
        return str(uuid4())

    def generate_message_id(self) -> str:
        """Generate a unique message ID."""
        return str(uuid4())

    def create_conversation_key(
        self,
        workspace_id: str,
        bot_id: str,
        channel_ref: str,
        user_ref: str,
        thread_id: Optional[str] = None,
    ) -> str:
        """Create a deterministic key for conversation lookup."""
        parts = [workspace_id, bot_id, channel_ref, user_ref]
        if thread_id:
            parts.append(thread_id)
        return ":".join(parts)
