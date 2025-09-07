from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
import json


class Conversation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    workspace_id: str = Field(index=True)
    bot_id: str = Field(index=True)
    channel_ref: str = Field(index=True)
    user_ref: str = Field(index=True)
    thread_id: Optional[str] = Field(default=None, index=True)
    state_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    messages: list["Message"] = Relationship(back_populates="conversation")

    @property
    def state(self) -> Dict[str, Any]:
        if not self.state_json:
            return {}
        return json.loads(self.state_json)

    @state.setter
    def state(self, value: Dict[str, Any]) -> None:
        self.state_json = json.dumps(value) if value else None
        self.updated_at = datetime.utcnow()


class Message(SQLModel, table=True):
    id: str = Field(primary_key=True)
    conversation_id: str = Field(index=True, foreign_key="conversation.id")
    role: str = Field(index=True)
    content: str
    metadata_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    conversation: Conversation | None = Relationship(back_populates="messages")

    @property
    def message_metadata(self) -> Dict[str, Any]:
        if not self.metadata_json:
            return {}
        return json.loads(self.metadata_json)

    @message_metadata.setter
    def message_metadata(self, value: Dict[str, Any]) -> None:
        self.metadata_json = json.dumps(value) if value else None

    def to_llm_message(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}
