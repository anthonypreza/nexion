import json
from datetime import datetime
from typing import Any

from sqlmodel import Field, Relationship, SQLModel

from ..core.types import ProviderMessage


class Conversation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    workspace_id: str = Field(index=True)
    bot_id: str = Field(index=True)
    channel_ref: str = Field(index=True)
    user_ref: str = Field(index=True)
    thread_id: str | None = Field(default=None, index=True)
    state_json: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    messages: list["Message"] = Relationship(back_populates="conversation")

    @property
    def state(self) -> dict[str, Any]:
        if not self.state_json:
            return {}
        return json.loads(self.state_json)

    @state.setter
    def state(self, value: dict[str, Any]) -> None:
        self.state_json = json.dumps(value) if value else None
        self.updated_at = datetime.utcnow()


class Message(SQLModel, table=True):
    id: str = Field(primary_key=True)
    conversation_id: str = Field(index=True, foreign_key="conversation.id")
    role: str = Field(index=True)
    content: str
    metadata_json: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    conversation: Conversation | None = Relationship(back_populates="messages")

    @property
    def message_metadata(self) -> dict[str, Any]:
        if not self.metadata_json:
            return {}
        return json.loads(self.metadata_json)

    @message_metadata.setter
    def message_metadata(self, value: dict[str, Any]) -> None:
        self.metadata_json = json.dumps(value) if value else None

    def to_llm_message(self) -> ProviderMessage:
        # Attempt to parse structured content (Anthropic-style blocks) if stored as JSON
        parsed = None
        try:
            parsed = json.loads(self.content)
        except Exception:
            parsed = None

        if isinstance(parsed, list):
            return ProviderMessage(role=self.role, content=parsed)
        return ProviderMessage(role=self.role, content=self.content)
