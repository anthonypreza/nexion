from ..config.bridge import get_config_bridge
from ..config.settings import BotSettings
from ..config.yaml import BotConfig, ChannelConfig, WorkspaceConfig
from ..core.agent import AgentRuntime
from ..storage import ConversationStore, SQLiteStore
from ..utils.logging import get_logger


class BotManager:
    def __init__(self, workspace_config: WorkspaceConfig, store: ConversationStore):
        """Initialize with workspace configuration and shared storage."""
        self.workspace_config = workspace_config
        self.store = store
        self.bots: dict[str, AgentRuntime] = {}
        self.http_routes: dict[str, str] = {}
        self.telegram_bots: dict[str, str] = {}
        self.logger = get_logger("bot_manager")

    def _create_settings_for_bot(self, bot_config: BotConfig) -> BotSettings:
        """Convert BotConfig to BotSettings with precedence: bot-level → global → defaults."""

        # Provider configuration with precedence
        openai_key = None
        anthropic_key = None
        max_tokens = 1024  # Default

        # Get global provider configs as defaults
        if "openai" in self.workspace_config.providers:
            global_openai = self.workspace_config.providers["openai"]
            openai_key = global_openai.api_key
            if global_openai.max_tokens:
                max_tokens = global_openai.max_tokens

        if "anthropic" in self.workspace_config.providers:
            global_anthropic = self.workspace_config.providers["anthropic"]
            anthropic_key = global_anthropic.api_key
            if global_anthropic.max_tokens:
                max_tokens = global_anthropic.max_tokens

        # Override with bot-level provider configs (higher precedence)
        if "openai" in bot_config.provider_config:
            bot_openai = bot_config.provider_config["openai"]
            if bot_openai.api_key:
                openai_key = bot_openai.api_key
            if bot_openai.max_tokens:
                max_tokens = bot_openai.max_tokens

        if "anthropic" in bot_config.provider_config:
            bot_anthropic = bot_config.provider_config["anthropic"]
            if bot_anthropic.api_key:
                anthropic_key = bot_anthropic.api_key
            if bot_anthropic.max_tokens:
                max_tokens = bot_anthropic.max_tokens

        # Step 3: Build channel-specific configurations
        channel_configs = {}
        for channel in bot_config.channels:
            if isinstance(channel, str):
                # Old format - use global adapter settings as fallback
                channel_configs[channel] = self._get_global_adapter_config_for_channel(
                    channel
                )
            elif isinstance(channel, ChannelConfig):
                # New format - merge bot-level config with global fallback
                global_config = self._get_global_adapter_config_for_channel(
                    channel.channel
                )
                # Bot-level config takes precedence
                merged_config = {**global_config, **channel.adapter_config}
                channel_configs[channel.channel] = merged_config

        return BotSettings(
            bot_id=bot_config.id,
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            model=bot_config.model,
            max_tokens=max_tokens,
            system_prompt_path=bot_config.system_prompt or "prompts/system.md",
            channel_configs=channel_configs,
            tools=bot_config.tools,
        )

    def _get_global_adapter_config_for_channel(self, channel: str) -> dict[str, str]:
        """Get global adapter configuration for a channel string."""
        if channel.startswith("http:"):
            if "http" in self.workspace_config.adapters:
                http_adapter = self.workspace_config.adapters["http"]
                return {"api_key": http_adapter.api_key} if http_adapter.api_key else {}
        elif channel.startswith("telegram:"):
            if "telegram" in self.workspace_config.adapters:
                telegram_adapter = self.workspace_config.adapters["telegram"]
                return (
                    {"bot_token": telegram_adapter.bot_token}
                    if telegram_adapter.bot_token
                    else {}
                )
        return {}

    async def initialize(self) -> None:
        """Parse configuration and auto-register all channels."""
        for bot_config in self.workspace_config.bots:
            bot_settings = self._create_settings_for_bot(bot_config)
            agent = AgentRuntime(bot_settings, self.store)
            self.bots[bot_config.id] = agent

            # Log provider/model summary for this bot
            provider_obj = getattr(agent, "provider", None)
            if provider_obj:
                provider_type = provider_obj.__class__.__name__.replace("Provider", "")
                provider_name = provider_type.lower()
                # agent.model is the resolved provider-specific name (without prefix)
                self.logger.info(
                    f"🧩 Bot '{bot_config.id}': provider={provider_name} model={agent.model} (configured={bot_config.model})"
                )
            else:
                self.logger.info(
                    f"🧩 Bot '{bot_config.id}': provider=none (echo mode) model={bot_config.model}"
                )

            # Auto-register all channels
            for channel in bot_config.channels:
                if isinstance(channel, str):
                    self._register_channel(channel, bot_config.id)
                elif isinstance(channel, ChannelConfig):
                    self._register_channel(channel.channel, bot_config.id)

            # Log channels configured for this bot
            channels = [
                c if isinstance(c, str) else c.channel for c in bot_config.channels
            ]
            self.logger.info(
                f"   ↳ channels: {', '.join(channels) if channels else '(none)'}"
            )

    def _register_channel(self, channel: str, bot_id: str):
        """Auto-register a channel for a bot."""
        if channel.startswith("http:"):
            path = channel[5:]
            self.http_routes[path] = bot_id
        elif channel.startswith("telegram:"):
            username = channel[9:]
            self.telegram_bots[username] = bot_id

    def get_bot_for_http_path(self, path: str) -> AgentRuntime | None:
        bot_id = self.http_routes.get(path)
        return self.bots.get(bot_id) if bot_id else None

    def get_bot_by_id(self, bot_id: str) -> AgentRuntime | None:
        """Get a specific bot by its ID."""
        return self.bots.get(bot_id)

    def get_bot_for_telegram(self, bot_username: str) -> AgentRuntime | None:
        """Get bot for Telegram username like '@supportbot'."""
        bot_id = self.telegram_bots.get(bot_username)
        return self.bots.get(bot_id) if bot_id else None

    def list_bots(self) -> list[str]:
        """List all bot IDs for debugging/admin."""
        return list(self.bots.keys())

    def get_workspace_id(self) -> str:
        """Get workspace identifier."""
        return self.workspace_config.workspace


# Global bot manager instance
_bot_manager: BotManager | None = None


async def get_bot_manager() -> BotManager:
    """Get or create the global bot manager."""
    global _bot_manager
    if _bot_manager is None:
        bridge = get_config_bridge()
        workspace_config = bridge.get_yaml_config()
        store = SQLiteStore()
        await store.initialize()  # Initialize the database schema
        _bot_manager = BotManager(workspace_config, store)
        await _bot_manager.initialize()
    return _bot_manager
