from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    # LLM
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    MODEL: str = "openai:gpt-4o-mini"

    # HTTP
    BOT_HTTP_KEY: str | None = None

    # Telegram
    TELEGRAM_BOT_TOKEN: str | None = None

    # Prompts
    SYSTEM_PROMPT_PATH: str = "prompts/system.md"

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
