from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..config.settings import BotSettings
from ..core.server import run
from .adapters import AdapterConfig, combine_adapters


class Bot:
    """Public Nexion bot interface."""

    def __init__(
        self,
        bot_id: str | None = None,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
        system_prompt_path: str | None = None,
        channel_configs: dict[str, dict[str, Any]] | None = None,
        adapters: list[AdapterConfig] | None = None,
        tools: list[str | Callable] | None = None,
        mcp_config: dict[str, Any] | None = None,
        mcp_file: str | None = None,
        settings: BotSettings | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.bot_id = bot_id
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.system_prompt_path = system_prompt_path
        self.channel_configs = channel_configs
        self.adapters = adapters
        self.tools = tools
        self.mcp_config = mcp_config
        self.mcp_file = mcp_file
        self.settings = self._create_settings() if settings is None else settings
        self.config_path = config_path

    @classmethod
    def from_settings(cls, settings: BotSettings) -> "Bot":
        return cls(
            bot_id=settings.bot_id,
            openai_api_key=settings.openai_api_key,
            anthropic_api_key=settings.anthropic_api_key,
            model=settings.model,
            max_tokens=settings.max_tokens,
            system_prompt_path=settings.system_prompt_path,
            channel_configs=settings.channel_configs,
            settings=settings,
        )

    @classmethod
    def from_yaml(cls, config_path: str) -> "Bot":
        config_path = Path(config_path) if config_path else None
        return cls(config_path=config_path)

    def run(self, port: int = 8080) -> None:
        if self.config_path:
            run(port=port, config_path=self.config_path)
        elif self.settings:
            run(port=port, settings=self.settings)
        else:
            run(port=port)

    def _process_tools(self) -> list[str]:
        """Process mixed tool types and return list of tool names."""
        if not self.tools:
            return []

        from ..tools.registry import get_tool_registry

        tool_names = []
        registry = get_tool_registry()

        for tool in self.tools:
            if isinstance(tool, str):
                # String tool name - add directly
                tool_names.append(tool)
            elif callable(tool):
                # Function object - check if it's decorated with @tool
                if hasattr(tool, "_tool_name"):
                    # Register the function and add its name
                    registry.register_function(tool)
                    tool_names.append(tool._tool_name)
                else:
                    raise ValueError(
                        f"Function {tool.__name__} is not decorated with @tool"
                    )
            else:
                raise ValueError(f"Tool must be string or callable, got {type(tool)}")

        return tool_names

    def _setup_mcp_config(self):
        """Handle MCP configuration setup."""
        if self.mcp_config:
            # Write inline MCP config to a temporary file or set env variable
            # For now, we'll log that this feature needs implementation
            import json
            import tempfile

            # Create a temporary mcp.json file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump({"mcpServers": self.mcp_config}, f, indent=2)
                # Store the temp file path for the agent runtime to use
                import os

                os.environ["NEXION_MCP_CONFIG_PATH"] = f.name
        elif self.mcp_file:
            # Point to custom MCP file
            import os

            os.environ["NEXION_MCP_CONFIG_PATH"] = self.mcp_file

    def _create_settings(self):
        # Process tools first
        processed_tools = self._process_tools()

        # Handle MCP configuration
        self._setup_mcp_config()

        # Determine channel_configs from either direct config or adapters
        channel_configs = self.channel_configs
        if channel_configs is None and self.adapters:
            channel_configs = combine_adapters(*self.adapters)

        settings = BotSettings(
            bot_id=self.bot_id or "default-bot",
            openai_api_key=self.openai_api_key,
            anthropic_api_key=self.anthropic_api_key,
            model=self.model or "openai:gpt-4o-mini",
            max_tokens=self.max_tokens,
            system_prompt=self.system_prompt,
            system_prompt_path=self.system_prompt_path or "prompts/system.md",
            channel_configs=channel_configs or {},
            tools=processed_tools,
        )
        return settings
