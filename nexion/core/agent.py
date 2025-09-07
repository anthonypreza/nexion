from pathlib import Path
from typing import Optional

from ..config.settings import Settings
from ..core.types import MessageEvent, Reply, ConversationContext, ProviderMessage
from ..providers.openai_ import OpenAIProvider
from ..providers.anthropic_ import AnthropicProvider
from ..storage.base import ConversationStore
from ..storage.sqlite import SQLiteStore
from ..utils.logging import get_logger


class AgentRuntime:
    def __init__(self, settings: Settings, store: Optional[ConversationStore] = None):
        self.settings = settings
        self.logger = get_logger("agent")

        # Initialize conversation store
        self.store = store or SQLiteStore()

        self.system_prompt = Path(settings.SYSTEM_PROMPT_PATH).read_text(
            encoding="utf-8"
        )

        if settings.OPENAI_API_KEY and settings.MODEL.startswith("openai"):
            self.provider = OpenAIProvider(settings.OPENAI_API_KEY)
            self.model = settings.MODEL.split(":", 1)[1]
            self.logger.info(f"🤖 Using OpenAI provider with model: {self.model}")
        elif settings.ANTHROPIC_API_KEY and settings.MODEL.startswith("anthropic"):
            self.provider = AnthropicProvider(settings.ANTHROPIC_API_KEY)
            self.model = settings.MODEL.split(":", 1)[1]
            self.logger.info(f"🤖 Using Anthropic provider with model: {self.model}")
        else:
            self.provider = None
            self.model = "echo"
            self.logger.info("🔄 No LLM provider configured, using echo mode")

    async def initialize(self) -> None:
        """Initialize the agent runtime and storage."""
        await self.store.initialize()
        self.logger.info("🚀 Agent runtime initialized with conversation storage")

    async def handle(self, event: MessageEvent) -> Reply:
        """Handle a message event with conversation context."""

        # Get or create a conversation
        conversation = await self.store.get_or_create_conversation(
            workspace_id=event.workspace_id,
            bot_id=event.bot_id,
            channel_ref=event.channel.value,
            user_ref=event.user_id,
            thread_id=event.thread_id,
        )

        # Store user message
        await self.store.add_message(
            conversation_id=conversation.id,
            role="user",
            content=event.text,
            metadata=event.metadata,
        )

        if not self.provider:
            reply_text = f"(echo) {event.text}"
        else:
            # Get conversation history
            history = await self.store.get_conversation_history(
                conversation.id, limit=10
            )

            # Build messages for LLM
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add conversation history
            for msg in history:
                messages.append(msg.to_llm_message())

            # Get response from LLM
            reply_text = await self.provider.chat(self.model, messages)

        # Store assistant response
        await self.store.add_message(
            conversation_id=conversation.id, role="assistant", content=reply_text
        )

        return Reply(text=reply_text)

    async def get_conversation_context(
        self, conversation_id: str
    ) -> Optional[ConversationContext]:
        """Get full conversation context for debugging/analysis."""
        conversation = await self.store.get_conversation_by_id(conversation_id)
        if not conversation:
            return None

        history = await self.store.get_conversation_history(conversation.id, limit=50)
        provider_messages = [
            ProviderMessage(role=msg.role, content=msg.content) for msg in history
        ]

        return ConversationContext(
            conversation_id=conversation.id,
            workspace_id=conversation.workspace_id,
            bot_id=conversation.bot_id,
            channel_ref=conversation.channel_ref,
            user_ref=conversation.user_ref,
            thread_id=conversation.thread_id,
            state=conversation.state,
            history=provider_messages,
        )
