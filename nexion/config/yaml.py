import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..utils.logging import get_logger

logger = get_logger("config")


@dataclass
class ProviderConfig:
    """Configuration for LLM providers."""

    api_key: str
    max_tokens: int | None = 1024


@dataclass
class HTTPAdapterConfig:
    """Configuration for HTTP adapters."""

    enabled: bool = True
    api_key: str | None = None


@dataclass
class TelegramAdapterConfig:
    """Configuration for Telegram adapters."""

    enabled: bool = True
    bot_token: str | None = None


@dataclass
class SlackAdapterConfig:
    """Configuration for Slack adapters."""

    enabled: bool = True
    app_token: str | None = None
    bot_token: str | None = None
    signing_secret: str | None = None


@dataclass
class DiscordAdapterConfig:
    """Configuration for Discord adapters."""

    enabled: bool = True
    bot_token: str | None = None


AdapterConfig = (
    HTTPAdapterConfig
    | TelegramAdapterConfig
    | SlackAdapterConfig
    | DiscordAdapterConfig
)


@dataclass
class KnowledgeBaseConfig:
    """Configuration for knowledge base."""

    id: str
    source: str  # Path to markdown files
    index: str = "bm25"  # Index type: bm25, embeddings, etc.


@dataclass
class ChannelConfig:
    """Configuration for a single channel with optional adapter overrides."""

    channel: str  # "http:/api/chat", "telegram:@mybotname"
    adapter_config: dict[str, Any] = field(
        default_factory=dict
    )  # Per-channel adapter config


@dataclass
class BotConfig:
    """Configuration for a single bot."""

    id: str
    channels: list[str | ChannelConfig] = field(
        default_factory=list
    )  # Support both old format ["http:/api/chat"] and new [ChannelConfig(...)]
    system_prompt: str | None = None  # Path to system prompt file
    flows: list[str] = field(default_factory=list)  # Path to flow YAML files
    model: str = "openai:gpt-4o-mini"
    tools: list[str] = field(default_factory=list)  # Tool names to enable
    provider_config: dict[str, ProviderConfig] = field(
        default_factory=dict
    )  # Per-bot provider overrides


@dataclass
class WorkspaceConfig:
    """Main configuration for the entire workspace."""

    workspace: str = "default"
    profiles: list[str] = field(default_factory=lambda: ["default"])

    # Core components
    bots: list[BotConfig] = field(default_factory=list)
    kb: list[KnowledgeBaseConfig] = field(default_factory=list)
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    adapters: dict[str, AdapterConfig] = field(default_factory=dict)


class ConfigLoader:
    """Loads and validates YAML configuration file."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or Path.cwd() / "bot.yml"

    def load(self) -> WorkspaceConfig:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Configuration file not found: {self.config_path}")
            return WorkspaceConfig()

        logger.info(f"Loading configuration from {self.config_path}")
        with open(self.config_path) as f:
            raw_config = yaml.safe_load(f)

        # Process env variable substitution
        processed_config = self._process_env_vars(raw_config)

        # Convert to dataclass
        config = self._dict_to_config(processed_config)

        logger.info(
            f"Loaded workspace configuration: {config.workspace} with {len(config.bots)} bots"
        )
        return config

    def _process_env_vars(self, data: Any) -> Any:
        """Recursively process env: prefixed values"""
        if isinstance(data, dict):
            return {key: self._process_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._process_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("env:"):
            env_var = data[4:]  # Remove "env:" prefix
            value = os.getenv(env_var)
            if value is None:
                logger.warning(f"Environment variable {env_var} not set")
            return value
        else:
            return data

    @staticmethod
    def _parse_bot_config(bot_data: dict[str, Any]) -> BotConfig:
        """Parse a bot configuration with support for both old and new channel formats."""
        parsed_bot = bot_data.copy()

        # Parse channels (support both old and new formats)
        if "channels" in parsed_bot:
            parsed_channels = []
            for channel_data in parsed_bot["channels"]:
                if isinstance(channel_data, str):
                    # Old format: "http:/api/chat"
                    parsed_channels.append(channel_data)
                elif isinstance(channel_data, dict):
                    # New format: {"channel": "http:/api/chat", "adapter_config": {...}}
                    if "channel" in channel_data:
                        parsed_channels.append(ChannelConfig(**channel_data))
                    else:
                        raise ValueError(
                            f"Channel config missing 'channel' field: {channel_data}"
                        )
                else:
                    raise ValueError(f"Invalid channel format: {channel_data}")
            parsed_bot["channels"] = parsed_channels

        # Parse provider_config
        if "provider_config" in parsed_bot:
            provider_configs = {}
            for provider_name, provider_data in parsed_bot["provider_config"].items():
                provider_configs[provider_name] = ProviderConfig(**provider_data)
            parsed_bot["provider_config"] = provider_configs

        return BotConfig(**parsed_bot)

    @staticmethod
    def _dict_to_config(data: dict[str, Any]) -> WorkspaceConfig:
        """Convert dictionary to WorkspaceConfig dataclass"""

        # Parse providers
        providers = {}
        if "providers" in data:
            for name, provider_data in data["providers"].items():
                providers[name] = ProviderConfig(**provider_data)

        # Parse adapters
        adapters = {}
        if "adapters" in data:
            for name, adapter_data in data["adapters"].items():
                if name == "http":
                    adapters[name] = HTTPAdapterConfig(**adapter_data)
                elif name == "telegram":
                    adapters[name] = TelegramAdapterConfig(**adapter_data)
                elif name == "discord":
                    adapters[name] = DiscordAdapterConfig(**adapter_data)
                elif name == "slack":
                    adapters[name] = SlackAdapterConfig(**adapter_data)
                else:
                    raise ValueError(f"Unknown adapter: {name}")

        # Parse knowledge bases
        kb = []
        if "kb" in data:
            for kb_data in data["kb"]:
                kb.append(KnowledgeBaseConfig(**kb_data))

        # Parse bots
        bots = []
        if "bots" in data:
            for bot_data in data["bots"]:
                bots.append(ConfigLoader._parse_bot_config(bot_data))

        return WorkspaceConfig(
            workspace=data.get("workspace", "default"),
            profiles=data.get("profiles", ["default"]),
            bots=bots,
            kb=kb,
            providers=providers,
            adapters=adapters,
        )


def load_config(config_path: Path | None = None) -> WorkspaceConfig:
    """Convenience function to load configuration"""
    loader = ConfigLoader(config_path)
    return loader.load()
