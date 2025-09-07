from pathlib import Path

from ..config.settings import Settings
from ..core.types import MessageEvent, Reply
from ..providers.openai_ import OpenAIProvider
from ..providers.anthropic_ import AnthropicProvider
from ..utils.logging import get_logger


class AgentRuntime:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("agent")

        self.sytem_prompt = Path(settings.SYSTEM_PROMPT_PATH).read_text(
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

    async def handle(self, event: MessageEvent) -> Reply:
        if not self.provider:
            return Reply(text=f"(echo) {event.text}")

        messages = [
            {"role": "system", "content": self.sytem_prompt},
            {"role": "user", "content": event.text},
        ]
        out = await self.provider.chat(self.model, messages)

        return Reply(text=out)
