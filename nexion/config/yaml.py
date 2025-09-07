import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from ..utils.logging import get_logger

logger = get_logger("config")


@dataclass
class ProviderConfig:
    """Configuration for LLM providers."""

    api_key: str


@dataclass
class HTTPAdapterConfig:
    """Configuration for HTTP adapters."""

    enabled: bool = True
    api_key: Optional[str] = None


@dataclass
class TelegramAdapterConfig:
    """Configuration for Telegram adapters."""

    enabled: bool = True
    bot_token: Optional[str] = None


@dataclass
class SlackAdapterConfig:
    """Configuration for Slack adapters."""

    enabled: bool = True
    app_token: Optional[str] = None
    bot_token: Optional[str] = None
    signing_secret: Optional[str] = None


@dataclass
class DiscordAdapterConfig:
    """Configuration for Discord adapters."""

    enabled: bool = True
    bot_token: Optional[str] = None


AdapterConfig = Union[
    HTTPAdapterConfig, TelegramAdapterConfig, SlackAdapterConfig, DiscordAdapterConfig
]


@dataclass
class KnowledgeBaseConfig:
    """Configuration for knowledge base."""

    id: str
    source: str  # Path to markdown files
    index: str = "bm25"  # Index type: bm25, embeddings, etc.


@dataclass
class BotConfig:
    """Configuration for a single bot."""

    id: str
    channels: List[str] = field(
        default_factory=list
    )  # ["http:/api/chat", "telegram:@mybotname"]
    system_prompt: Optional[str] = None  # Path to system prompt file
    flows: List[str] = field(default_factory=list)  # Path to flow YAML files
    model: str = "openai:gpt-4o-mini"
    tools: List[str] = field(default_factory=list)  # Tool names to enable


@dataclass
class WorkspaceConfig:
    """Main configuration for the entire workspace."""

    workspace: str = "default"
    profiles: List[str] = field(default_factory=lambda: ["default"])

    # Core components
    bots: List[BotConfig] = field(default_factory=list)
    kb: List[KnowledgeBaseConfig] = field(default_factory=list)
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    adapters: Dict[str, AdapterConfig] = field(default_factory=dict)


class ConfigLoader:
    """Loads and validates YAML configuration file."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.cwd() / "bot.yml"

    def load(self) -> WorkspaceConfig:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Configuration file not found: {self.config_path}")
            return WorkspaceConfig()

        logger.info(f"Loading configuration from {self.config_path}")
        with open(self.config_path, "r") as f:
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
    def _dict_to_config(data: Dict[str, Any]) -> WorkspaceConfig:
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
                bots.append(BotConfig(**bot_data))

        return WorkspaceConfig(
            workspace=data.get("workspace", "default"),
            profiles=data.get("profiles", ["default"]),
            bots=bots,
            kb=kb,
            providers=providers,
            adapters=adapters,
        )


def load_config(config_path: Optional[Path] = None) -> WorkspaceConfig:
    """Convenience function to load configuration"""
    loader = ConfigLoader(config_path)
    return loader.load()
