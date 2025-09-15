"""Adapter configuration builders for programmatic bot creation."""

from abc import ABC, abstractmethod
from typing import Any


class AdapterConfig(ABC):
    """Base class for adapter configurations."""

    def __init__(self, adapter_type: str):
        self.adapter_type = adapter_type
        self._config: dict[str, Any] = {}

    @abstractmethod
    def build(self) -> dict[str, dict[str, Any]]:
        """Build the channel_configs dict format expected by BotSettings."""
        raise NotImplementedError("Must be implemented by subclass")


class DiscordConfig(AdapterConfig):
    """Configuration builder for Discord adapter."""

    def __init__(self, bot_token: str, channel: str | None = None):
        super().__init__("discord")
        self.bot_token = bot_token
        self.channel = channel or "@default"

    def build(self) -> dict[str, dict[str, Any]]:
        """Build Discord channel configuration."""
        channel_key = f"discord:{self.channel}"
        return {channel_key: {"bot_token": self.bot_token}}


class TelegramConfig(AdapterConfig):
    """Configuration builder for Telegram adapter."""

    def __init__(self, bot_token: str, channel: str | None = None):
        super().__init__("telegram")
        self.bot_token = bot_token
        self.channel = channel or "@default"

    def build(self) -> dict[str, dict[str, Any]]:
        """Build Telegram channel configuration."""
        channel_key = f"telegram:{self.channel}"
        return {channel_key: {"bot_token": self.bot_token}}


class HttpConfig(AdapterConfig):
    """Configuration builder for HTTP adapter."""

    def __init__(self, api_key: str | None = None, endpoint: str = "/api/chat"):
        super().__init__("http")
        self.api_key = api_key
        self.endpoint = endpoint

    def build(self) -> dict[str, dict[str, Any]]:
        """Build HTTP channel configuration."""
        channel_key = f"http:{self.endpoint}"
        config = {}
        if self.api_key:
            config["api_key"] = self.api_key
        return {channel_key: config}


def combine_adapters(*adapters: AdapterConfig) -> dict[str, dict[str, Any]]:
    """Combine multiple adapter configurations into a single channel_configs dict."""
    combined = {}
    for adapter in adapters:
        combined.update(adapter.build())
    return combined
