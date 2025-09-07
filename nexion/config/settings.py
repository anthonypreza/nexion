from pathlib import Path
from typing import Any

from pydantic import BaseSettings


class BotSettings(BaseSettings):
    """Settings for a single bot instance."""

    # Bot identity
    bot_id: str

    # LLM Configuration
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    model: str = "openai:gpt-4o-mini"
    max_tokens: int | None = 1024

    # System prompt
    system_prompt_path: str = "prompts/system.md"

    # Channel-specific adapter configurations
    # Format: {"http:/api/support": {"api_key": "key123"}, "telegram:@supportbot": {"bot_token": "token456"}}
    channel_configs: dict[str, dict[str, Any]] = {}

    def __init__(self, **kwargs):
        # Load .env from current working directory first
        env_file = Path.cwd() / ".env"
        if env_file.exists():
            from dotenv import load_dotenv

            load_dotenv(env_file)

        # Initialize with environment variables and passed kwargs
        super().__init__(**kwargs)

    class Config:
        # Allow environment variable overrides
        env_file = None  # We handle .env loading manually
        case_sensitive = False


# Legacy alias for backwards compatibility during transition
Settings = BotSettings
