from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel, create_engine, Session, select
from datetime import datetime
import json

from .base import ConversationStore
from .models import Conversation, Message
from ..utils.logging import get_logger


class SQLiteStore(ConversationStore):
    """SQLite implementation of ConversationStore."""
    
    def __init__(self, db_path: str = "./nexion.db"):
        self.db_path = Path(db_path)
        self.logger = get_logger("sqlite_store")
        
        # Create SQLite engine with proper settings
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,  # Set to True for SQL debugging
            connect_args={"check_same_thread": False}  # Allow multi-threading
        )
        
    async def initialize(self) -> None:
        """Initialize SQLite database and create tables."""
        self.logger.info(f"Initializing SQLite database at {self.db_path}")
        
        # Create all tables
        SQLModel.metadata.create_all(self.engine)
        
        self.logger.info("SQLite database initialized successfully")
    
    async def get_or_create_conversation(
        self, 
        workspace_id: str,
        bot_id: str, 
        channel_ref: str, 
        user_ref: str, 
        thread_id: Optional[str] = None
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        
        with Session(self.engine) as session:
            # Try to find existing conversation
            statement = select(Conversation).where(
                Conversation.workspace_id == workspace_id,
                Conversation.bot_id == bot_id,
                Conversation.channel_ref == channel_ref,
                Conversation.user_ref == user_ref,
                Conversation.thread_id == thread_id
            )
            
            conversation = session.exec(statement).first()
            
            if conversation:
                # Update timestamp on existing conversation
                conversation.updated_at = datetime.utcnow()
                session.add(conversation)
                session.commit()
                session.refresh(conversation)
                return conversation
            
            # Create new conversation
            conversation = Conversation(
                id=self.generate_conversation_id(),
                workspace_id=workspace_id,
                bot_id=bot_id,
                channel_ref=channel_ref,
                user_ref=user_ref,
                thread_id=thread_id
            )
            
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            
            self.logger.debug(f"Created new conversation: {conversation.id}")
            return conversation
    
    async def add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Add a message to a conversation."""
        
        message = Message(
            id=self.generate_message_id(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_json=json.dumps(metadata) if metadata else None
        )
        
        with Session(self.engine) as session:
            session.add(message)
            
            # Update conversation timestamp
            conversation = session.get(Conversation, conversation_id)
            if conversation:
                conversation.updated_at = datetime.utcnow()
                session.add(conversation)
            
            session.commit()
            session.refresh(message)
            
        self.logger.debug(f"Added message to conversation {conversation_id}")
        return message
    
    async def get_conversation_history(
        self, 
        conversation_id: str, 
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages for a conversation, ordered by created_at ASC."""
        
        with Session(self.engine) as session:
            statement = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            
            messages = session.exec(statement).all()
            # Return in chronological order (oldest first) for LLM context
            return list(reversed(messages))
    
    async def update_conversation_state(
        self, 
        conversation_id: str, 
        state: Dict[str, Any]
    ) -> None:
        """Update conversation state/metadata."""
        
        with Session(self.engine) as session:
            conversation = session.get(Conversation, conversation_id)
            if conversation:
                conversation.state = state
                session.add(conversation)
                session.commit()
    
    async def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        
        with Session(self.engine) as session:
            return session.get(Conversation, conversation_id)
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        
        with Session(self.engine) as session:
            # Delete messages first (due to foreign key constraint)
            message_statement = select(Message).where(Message.conversation_id == conversation_id)
            messages = session.exec(message_statement).all()
            for message in messages:
                session.delete(message)
            
            # Delete conversation
            conversation = session.get(Conversation, conversation_id)
            if conversation:
                session.delete(conversation)
                session.commit()
                return True
            
            return False
