from pathlib import Path
from typing import Optional
from .settings import Settings
from .yaml import load_config, WorkspaceConfig
from ..utils.logging import get_logger

logger = get_logger("config_bridge")


class ConfigBridge:
    """Bridges YAML configuration with Settings system."""

    def __init__(self, config_path: Optional[Path] = None):
        # Load .env from current working directory first
        env_file = Path.cwd() / ".env"
        if env_file.exists():
            from dotenv import load_dotenv

            load_dotenv(env_file)
            logger.info(f"Loaded .env file from {env_file}")

        self.yaml_config = load_config(config_path)
        self._settings_cache: Optional[Settings] = None

    def get_settings(self) -> Settings:
        """Convert YAML configuration to Settings object."""
        if self._settings_cache is not None:
            return self._settings_cache

        openai_api_key = None
        anthropic_api_key = None

        if "openai" in self.yaml_config.providers:
            openai_api_key = self.yaml_config.providers["openai"].api_key
        if "anthropic" in self.yaml_config.providers:
            anthropic_api_key = self.yaml_config.providers["anthropic"].api_key

        # Extract adapter settings
        bot_http_key = None
        telegram_bot_token = None

        if "http" in self.yaml_config.adapters:
            bot_http_key = self.yaml_config.adapters["http"].api_key
        if "telegram" in self.yaml_config.adapters:
            telegram_bot_token = self.yaml_config.adapters["telegram"].bot_token

        # Get model from first bot
        model = "openai:gpt-4o-mini"
        system_prompt_path = "prompts/system.md"

        if self.yaml_config.bots:
            first_bot = self.yaml_config.bots[0]
            model = first_bot.model
            if first_bot.system_prompt:
                system_prompt_path = first_bot.system_prompt

        self._settings_cache = Settings(
            OPENAI_API_KEY=openai_api_key,
            ANTHROPIC_API_KEY=anthropic_api_key,
            MODEL=model,
            BOT_HTTP_KEY=bot_http_key,
            TELEGRAM_BOT_TOKEN=telegram_bot_token,
            SYSTEM_PROMPT_PATH=system_prompt_path,
        )

        logger.info(
            f"Bridged YAML config to Settings: model={model}, providers={len(self.yaml_config.providers)}"
        )
        return self._settings_cache

    def get_yaml_config(self) -> WorkspaceConfig:
        """Get the full YAML configuration."""
        return self.yaml_config


# Global config bridge instance
_config_bridge: Optional[ConfigBridge] = None


def get_config_bridge(config_path: Optional[Path] = None) -> ConfigBridge:
    """Get or create the global config bridge."""
    global _config_bridge
    if _config_bridge is None:
        _config_bridge = ConfigBridge(config_path)
    return _config_bridge


def get_settings_from_yaml(config_path: Optional[Path] = None) -> Settings:
    """Convenience function to get settings from a YAML file."""
    bridge = get_config_bridge(config_path)
    return bridge.get_settings()
