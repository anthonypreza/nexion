# Programmatic SDK Example

This example demonstrates how to create Nexion bots entirely in Python code, giving you maximum control and flexibility. Unlike YAML-based configuration, the programmatic approach allows for dynamic bot creation, conditional logic, and tight integration with your existing Python applications.

## Features Demonstrated

- **Pure Python Configuration**: No YAML files needed
- **Custom Tool Creation**: Define tools using the `@tool` decorator
- **Environment Variable Resolution**: Automatic `env:` prefix handling
- **HTTP Adapter**: Simple REST API interface
- **Mixed Tool Types**: Combine function objects and string references
- **MCP Integration**: Inline MCP server configuration

## Quick Start

1. **Copy environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

2. **Run the bot:**
   ```bash
   python bot.py
   ```

3. **Test the bot:**
   ```bash
   curl -X POST http://localhost:8080/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Can you greet Alice in a formal style?"}'
   ```

## Key Advantages of Programmatic Configuration

### 1. **Dynamic Bot Creation**
```python
# Create bots based on runtime conditions
bot_config = get_user_preferences()
bot = Bot(
    bot_id=f"user-{user_id}",
    model=bot_config.preferred_model,
    tools=get_user_tools(user_id),
    adapters=[HttpConfig(endpoint=f"/api/{user_id}")]
)
```

### 2. **Custom Tool Integration**
```python
@tool("database_query", "Query the user database")
def query_database(query: str) -> str:
    # Direct integration with your existing systems
    return database.execute(query)

bot = Bot(tools=[query_database])
```

### 3. **Conditional Configuration**
```python
# Different setups for development vs production
if environment == "production":
    adapters = [DiscordConfig(...), SlackConfig(...)]
else:
    adapters = [HttpConfig(endpoint="/api/dev")]

bot = Bot(adapters=adapters)
```

### 4. **Type Safety and IDE Support**
- Full IntelliSense and type checking
- Compile-time error detection
- Refactoring support

## Configuration Options

### Bot Parameters
```python
Bot(
    bot_id="my-bot",                    # Unique identifier
    model="openai:gpt-4o-mini",         # LLM model
    openai_api_key="env:OPENAI_API_KEY", # API keys (env vars supported)
    anthropic_api_key="...",            # Alternative LLM provider
    max_tokens=1024,                    # Response length limit
    system_prompt="You are a helpful assistant...", # Inline system prompt
    system_prompt_path="prompts/system.md", # Alternative: load from file
    tools=[...],                        # Tool functions and names
    adapters=[...],                     # Channel adapters
    mcp_config={...},                   # Inline MCP configuration
    mcp_file="custom-mcp.json"          # Custom MCP file path
)
```

### Available Adapters
```python
from nexion import Bot, HttpConfig, DiscordConfig, TelegramConfig

# HTTP REST API
HttpConfig(api_key="...", endpoint="/api/chat")

# Discord bot
DiscordConfig(bot_token="...", channel="@my-bot")

# Telegram bot
TelegramConfig(bot_token="...", channel="@my-bot")
```

### Tool Definition
```python
from nexion.tools import tool

@tool("tool_name", "Description for the LLM")
def my_tool(param1: str, param2: int = 42) -> str:
    """Detailed docstring for parameter descriptions.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter with default
    """
    return f"Processed {param1} with {param2}"
```

### MCP Tools

You can also reference MCP (Model Context Protocol) tools by name. These tools are discovered from MCP servers and require proper server configuration:

```python
bot = Bot(
    tools=[
        my_custom_tool,                    # Function object
        "mcp__filesystem__read_file",      # MCP tool reference
    ],
    mcp_config={
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
    }
)
```

**Important**: If an MCP tool reference isn't found during startup:
- Check that the MCP server is properly configured and starts successfully
- Verify the tool name matches exactly what the server provides
- Check the application logs for MCP discovery messages

## Extending the SDK

The programmatic approach makes it easy to extend Nexion with custom functionality:

### Custom Adapters
```python
from nexion.sdk.adapters import AdapterConfig

class CustomAdapterConfig(AdapterConfig):
    def __init__(self, custom_param: str):
        super().__init__("custom")
        self.custom_param = custom_param

    def build(self) -> dict:
        return {
            f"custom:{self.custom_param}": {
                "param": self.custom_param
            }
        }
```

### Dynamic Tool Loading
```python
def load_tools_from_directory(directory: str):
    tools = []
    for file in Path(directory).glob("*.py"):
        module = importlib.import_module(file.stem)
        for name, obj in inspect.getmembers(module):
            if callable(obj) and hasattr(obj, '_tool_name'):
                tools.append(obj)
    return tools

bot = Bot(tools=load_tools_from_directory("./my_tools"))
```

### Bot Factory Pattern
```python
class BotFactory:
    @staticmethod
    def create_support_bot(user_id: str) -> Bot:
        return Bot(
            bot_id=f"support-{user_id}",
            tools=[escalate_ticket, search_knowledge_base],
            adapters=[HttpConfig(endpoint=f"/support/{user_id}")]
        )

    @staticmethod
    def create_analytics_bot() -> Bot:
        return Bot(
            bot_id="analytics",
            tools=[query_metrics, generate_report],
            adapters=[SlackConfig(channel="#analytics")]
        )
```

## Contributing

We encourage contributions to expand the SDK capabilities:

1. **New Adapters**: Add support for more platforms (Slack, WhatsApp, etc.)
2. **Tool Utilities**: Create helper functions for common tool patterns
3. **Configuration Builders**: Develop fluent APIs for complex setups
4. **Runtime Extensions**: Add support for dynamic bot modification

See the main [Contributing Guide](../../CONTRIBUTING.md) for details.

## Next Steps

- Explore the [Discord Bot Example](../discord-bot/) for platform-specific integration
- Check out [MCP Integration](../mcp-example/) for external tool capabilities
- Review [Multi-Bot Setup](../multi-tenant-bots/) for advanced deployments
