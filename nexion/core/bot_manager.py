from typing import Optional, List, Dict

from ..config.bridge import get_config_bridge
from ..config.settings import Settings
from ..config.yaml import WorkspaceConfig, BotConfig
from ..core.agent import AgentRuntime
from ..storage import ConversationStore, SQLiteStore


class BotManager:
    def __init__(self, workspace_config: WorkspaceConfig, store: ConversationStore):
        """Initialize with workspace configuration and shared storage."""
        self.workspace_config = workspace_config
        self.store = store
        self.bots: Dict[str, AgentRuntime] = {}
        self.http_routes: Dict[str, str] = {}
        self.telegram_bots: Dict[str, str] = {}

    def _create_settings_for_bot(self, bot_config: BotConfig) -> Settings:
        """Convert BotConfig to Settings for AgentRuntime."""
        # Get provider keys
        openai_key = None
        anthropic_key = None

        if "openai" in self.workspace_config.providers:
            openai_key = self.workspace_config.providers["openai"].api_key
        if "anthropic" in self.workspace_config.providers:
            anthropic_key = self.workspace_config.providers["anthropic"].api_key

        # Get adapter settings from workspace config
        http_key = None
        telegram_token = None

        if "http" in self.workspace_config.adapters:
            http_key = self.workspace_config.adapters["http"].api_key
        if "telegram" in self.workspace_config.adapters:
            telegram_token = self.workspace_config.adapters["telegram"].bot_token

        return Settings(
            OPENAI_API_KEY=openai_key,
            ANTHROPIC_API_KEY=anthropic_key,
            MODEL=bot_config.model,
            SYSTEM_PROMPT_PATH=bot_config.system_prompt or "prompts/system.md",
            BOT_HTTP_KEY=http_key,
            TELEGRAM_BOT_TOKEN=telegram_token,
        )

    async def initialize(self) -> None:
        """Parse configuration and auto-register all channels."""
        for bot_config in self.workspace_config.bots:
            bot_settings = self._create_settings_for_bot(bot_config)
            agent = AgentRuntime(bot_settings, self.store)
            self.bots[bot_config.id] = agent

            # Auto-register all channels
            for channel in bot_config.channels:
                self._register_channel(channel, bot_config.id)

    def _register_channel(self, channel: str, bot_id: str):
        """Auto-register a channel for a bot."""
        if channel.startswith("http:"):
            path = channel[5:]
            self.http_routes[path] = bot_id
        elif channel.startswith("telegram:"):
            username = channel[9:]
            self.telegram_bots[username] = bot_id

    def get_bot_for_http_path(self, path: str) -> Optional[AgentRuntime]:
        bot_id = self.http_routes.get(path)
        return self.bots.get(bot_id) if bot_id else None

    def get_bot_by_id(self, bot_id: str) -> Optional[AgentRuntime]:
        """Get a specific bot by its ID."""
        return self.bots.get(bot_id)

    def get_bot_for_telegram(self, bot_username: str) -> Optional[AgentRuntime]:
        """Get bot for Telegram username like '@supportbot'."""
        bot_id = self.telegram_bots.get(bot_username)
        return self.bots.get(bot_id) if bot_id else None

    def list_bots(self) -> List[str]:
        """List all bot IDs for debugging/admin."""
        return list(self.bots.keys())

    def get_workspace_id(self) -> str:
        """Get workspace identifier."""
        return self.workspace_config.workspace


# Global bot manager instance
_bot_manager: Optional[BotManager] = None


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
