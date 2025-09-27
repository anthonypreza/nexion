# Nexion

> An open-source AI agent framework for building LLM bots that can be deployed across multiple channels

Nexion lets you build AI-powered bots using simple YAML configuration and deploy them to HTTP endpoints, Telegram, and Discord. Perfect for creating support bots, documentation assistants, and interactive AI experiences.

## ⚠️ Project Status: Experimental

- Not production-ready: the project is under active development and APIs, configuration, and behavior may change without notice.
- Expect breaking changes and incomplete features while the design stabilizes.
- Use for prototypes, experiments, and local development — avoid production deployments for now.
- Pin versions or specific commits if you rely on behavior; review changes before updating.
- Feedback and contributions are welcome as we iterate.

## 🔐 Security Guidance

- Remote MCP servers you do not control are a security risk. They may read/write files, make network requests, or exfiltrate data depending on the tools they expose.
- Only enable trusted tools and MCP servers. Prefer local or self-hosted MCP servers that you operate.
- Apply least privilege: enable the minimum set of tools per-bot and per-environment; review `mcp.json` and tool names (`mcp__<server>__<tool>`) before use.
- Keep secrets in `.env` and reference them via `env:` in config; never commit secrets.
- Use separate API keys for development vs. production and rotate them regularly.
- Treat HTTP adapter API keys as credentials; do not expose them in client code or public demos.

## ✨ Current Features

- **🤖 Multi-LLM Support**: OpenAI (Responses API) and Anthropic integration with your API keys
- **🌐 Dynamic HTTP Interfaces**: Multiple bots with individual web UIs and REST APIs
- **🎯 Multi-Bot Architecture**: Run multiple specialized bots from a single configuration
- **📱 Telegram Integration**: Direct message conversations via polling (no webhooks needed)
- **💬 Discord Integration**: Direct message conversations via WebSocket with resume/reconnect and bot filtering
- **💾 Persistent Conversations**: SQLite-based conversation history
- **📝 YAML Configuration**: Simple, declarative bot configuration with environment variable support
- **🐍 Programmatic SDK**: Create bots entirely in Python code for maximum control and flexibility
- **🔧 CLI Tools**: Bootstrap projects and run development servers
- **🎨 Custom System Prompts**: Personalize each bot's personality and behavior
- **🔄 Pre-commit Hooks**: Automated code formatting with Ruff
- **🔗 MCP Integration**: Discover and use MCP servers/tools via `mcp.json`

## 🚀 Quick Start

### 1. Install Nexion

```bash
# Clone and install
git clone https://github.com/anthonypreza/nexion
cd nexion
uv sync
```

**For Contributors:**
```bash
uv sync --group dev  # Install development dependencies
pre-commit install   # Set up code formatting hooks
```

### 2. Bootstrap a New Bot Project

```bash
nexctl init my-bot
cd my-bot
```

This creates:
- `bot.yml` - Bot configuration
- `prompts/system.md` - System prompt template
- `.env.example` - Environment variables template

### 3. Configure Your Bot

Edit `bot.yml`:

```yaml
workspace: my-bot
profiles: [default]

bots:
  - id: my-assistant
    channels:
      - "http:/api/chat"
    system_prompt: prompts/system.md
    model: openai:gpt-4o-mini

providers:
  openai:
    api_key: env:OPENAI_API_KEY

adapters:
  http:
    api_key: env:BOT_HTTP_KEY
```

### 4. Set Up Environment

Copy `.env.example` to `.env` and add your API keys:

```bash
OPENAI_API_KEY=your_openai_api_key_here
BOT_HTTP_KEY=dev-secret  # For development only
```

### 5. Start Your Bot

```bash
nexctl dev
```

Visit **http://localhost:8080** to chat with your bot! 🎉

## 🐍 Programmatic Bot Creation (Maximum Control)

For advanced use cases, you can create bots entirely in Python code without YAML configuration. This approach provides maximum flexibility, type safety, and integration with existing Python applications.

### Why Choose Programmatic Configuration?

- **🎯 Dynamic Configuration**: Create bots based on runtime conditions
- **🔒 Type Safety**: Full IntelliSense and compile-time error checking
- **🔧 Custom Integration**: Direct integration with existing systems and databases
- **🚀 Conditional Logic**: Different setups for development vs production
- **📦 No External Files**: Self-contained bot definitions

### Quick Example

```python
from nexion import Bot, HttpConfig
from nexion.tools import tool

@tool("greet", "Greet users with personalized messages")
def greet_user(name: str, style: str = "friendly") -> str:
    styles = {
        "friendly": f"Hello {name}! 👋 Great to meet you!",
        "formal": f"Good day, {name}. Pleased to meet you.",
        "casual": f"Hey {name}! What's up?"
    }
    return styles.get(style, styles["friendly"])

# Create bot programmatically
bot = Bot(
    bot_id="my-programmatic-bot",
    model="openai:gpt-4o-mini",
    openai_api_key="env:OPENAI_API_KEY",
    adapters=[HttpConfig(endpoint="/api/chat")],
    tools=[greet_user],  # Pass function objects directly!
    system_prompt_path="prompts/system.md"
)

if __name__ == "__main__":
    bot.run()  # Start the bot
```

### Advanced Features

**Mixed Tool Types:**
```python
tools=[
    my_custom_function,           # Decorated function object
    "mcp__filesystem__read_file",   # String reference to MCP tool
]
```

**Dynamic Bot Creation:**
```python
def create_user_bot(user_id: str, preferences: dict) -> Bot:
    return Bot(
        bot_id=f"user-{user_id}",
        model=preferences.get("model", "openai:gpt-4o-mini"),
        tools=get_user_tools(user_id),
        adapters=[HttpConfig(endpoint=f"/api/{user_id}")]
    )
```

**Inline MCP Configuration:**
```python
Bot(
    # ... other config ...
    mcp_config={
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
    }
)
```

### Complete Example

Check out the [Programmatic SDK Example](examples/programmatic-sdk/) for a full-featured demonstration with custom tools, environment variable handling, and comprehensive documentation.

### Contributing to the SDK

We encourage contributions to expand the programmatic SDK:

- **🔌 New Adapters**: Add support for more platforms (Slack, WhatsApp, etc.)
- **🛠️ Tool Utilities**: Create helper functions for common tool patterns
- **🏗️ Configuration Builders**: Develop fluent APIs for complex setups
- **⚡ Runtime Extensions**: Add support for dynamic bot modification

## 📚 Configuration Reference

### Complete bot.yml Schema

```yaml
# Root configuration
workspace: string                 # Workspace identifier
profiles: [string, ...]          # Configuration profiles (default: ["default"])
log_level: string                 # Optional: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Bot definitions
bots:
  - id: string                    # Required: Unique bot identifier
    channels: [string, ...]       # Channel bindings (see Channel Syntax below)
    system_prompt: string         # Path to system prompt file (default: prompts/system.md)
    model: string                 # LLM model (default: "openai:gpt-4o-mini")
    flows: [string, ...]          # Flow YAML paths (coming soon)
    tools: [string, ...]          # Enabled tools (names from your tool registry)

# LLM provider configuration
providers:
  openai:
    api_key: string               # OpenAI API key (supports env: prefix)
  anthropic:
    api_key: string               # Anthropic API key (supports env: prefix)

# Channel adapter configuration
adapters:
  http:
    enabled: boolean              # Enable HTTP adapter (default: true)
    api_key: string               # API key for authentication (optional)
  telegram:
    enabled: boolean              # Enable Telegram adapter (default: true)
    bot_token: string             # Telegram bot token (optional)
  discord:
    enabled: boolean              # Enable Discord adapter (default: true)
    bot_token: string             # Discord bot token (optional)

# Knowledge bases (coming soon)
kb:
  - id: string                    # Unique KB identifier
    source: string                # Path to markdown files
    index: string                 # Index type: "bm25" (default)
```

### Channel Syntax

Channels define where your bot receives and sends messages:

| Channel | Syntax | Description |
|---------|--------|-------------|
| HTTP | `http:/api/chat` | HTTP endpoint at `/api/chat` |
| HTTP | `http:/api/custom` | HTTP endpoint at `/api/custom` |
| Telegram | `telegram:@mybotname` | Telegram bot username |
| Discord | `discord:@mybotname` | Discord bot username |

**Examples:**
```yaml
channels:
  - "http:/api/chat"        # HTTP endpoint
  - "telegram:@supportbot"  # Telegram bot
  - "discord:@mybot"        # Discord bot
```

### Environment Variables

Use `env:VARIABLE_NAME` syntax to reference environment variables:

```yaml
providers:
  openai:
    api_key: env:OPENAI_API_KEY    # Reads from $OPENAI_API_KEY

adapters:
  http:
    api_key: env:BOT_HTTP_KEY      # Reads from $BOT_HTTP_KEY
```

### Model Options

Nexion supports any model available from the OpenAI or Anthropic APIs. Use the `provider:model-name` format:

**OpenAI Models:**
Use any OpenAI model with the `openai:` prefix:
- `openai:gpt-4o-mini` (default)
- `openai:gpt-4o`
- `openai:gpt-4-turbo`
- `openai:gpt-3.5-turbo`
- `openai:o1-preview`
- `openai:o1-mini`
- Any other OpenAI model available via their API

**Anthropic Models:**
Use any Anthropic model with the `anthropic:` prefix:
- `anthropic:claude-3-5-haiku-latest`
- `anthropic:claude-3-5-sonnet-latest`
- `anthropic:claude-3-opus-latest`
- `anthropic:claude-3-haiku-20240307`
- Any other Claude model available via their API

**Examples:**
```yaml
bots:
  - id: my-bot
    model: openai:gpt-4o-mini     # Default
  - id: advanced-bot
    model: anthropic:claude-3-5-sonnet-latest
  - id: reasoning-bot
    model: openai:o1-preview
```

## 📖 Configuration Examples

### Minimal HTTP Bot

```yaml
workspace: simple-bot
bots:
  - id: assistant
    channels: ["http:/api/chat"]
    model: openai:gpt-4o-mini

providers:
  openai:
    api_key: env:OPENAI_API_KEY

adapters:
  http:
    api_key: env:BOT_HTTP_KEY
```

### Multi-Channel Bot

```yaml
workspace: support-bot
bots:
  - id: support-assistant
    channels:
      - "http:/api/chat"
      - "telegram:@supportbot"
    system_prompt: prompts/support.md
    model: openai:gpt-4o

providers:
  openai:
    api_key: env:OPENAI_API_KEY

adapters:
  http:
    api_key: env:BOT_HTTP_KEY
  telegram:
    bot_token: env:TELEGRAM_BOT_TOKEN
```

### Multi-Bot Specialized Setup

```yaml
workspace: specialized-bots
bots:
  - id: faq-bot
    channels: ["http:/api/faq/chat"]
    system_prompt: prompts/faq.md
    model: openai:gpt-4o-mini
  - id: sales-bot
    channels: ["http:/api/sales/chat"]
    system_prompt: prompts/sales.md
    model: anthropic:claude-3-5-sonnet-latest

providers:
  openai:
    api_key: env:OPENAI_API_KEY
  anthropic:
    api_key: env:ANTHROPIC_API_KEY

adapters:
  http:
    api_key: env:BOT_HTTP_KEY
```

**Features:**
- Each bot has its own web UI at `/ui/faq/chat` and `/ui/sales/chat`
- Navigation between bots in the web interface
- Dedicated API endpoints for each bot
- Specialized system prompts for different use cases

## 🔌 Adapters

### HTTP Adapter

The HTTP adapter provides dynamic web UIs and REST APIs for each bot:

**Multi-Bot Web UI**:
- Main UI at `http://localhost:8080/` shows all available bots
- Individual bot UIs at `/ui/{path}` (e.g., `/ui/faq/chat`, `/ui/sales/chat`)
- Navigation between bots with dedicated interfaces
- Automatic redirect to single bot UI when only one bot is configured

**Dynamic REST APIs**: Each bot gets its own endpoint

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-secret" \
  -d '{
    "user_id": "user123",
    "message": "Hello!",
    "bot_id": "default"
  }'
```

**Response:**
```json
{
  "reply": "Hello! How can I help you today?"
}
```

**Authentication:**
- Optional API key via `Authorization: Bearer <key>` header
- Configure via `adapters.http.api_key` in bot.yml
- Use "dev-secret" for local development

### Telegram Adapter

The Telegram adapter uses polling mode for direct message conversations (no webhooks required):

**Setup:**
1. Create a bot with @BotFather on Telegram
2. Get your bot token
3. Set `TELEGRAM_BOT_TOKEN` environment variable
4. Configure channels with `telegram:@yourbotname`

**Features:**
- Automatic polling startup when token is configured
- No webhook setup required - perfect for local development
- Direct message conversations with users

### Discord Adapter

The Discord adapter uses WebSocket connections for real-time direct message conversations:

**Setup:**
1. Create a Discord Application at https://discord.com/developers/applications
2. Create a bot and copy the bot token
3. Enable "Message Content Intent" in bot settings
4. Set `DISCORD_BOT_TOKEN` environment variable
5. Configure channels with `discord:@yourbotname`

**Features:**
- Real-time WebSocket connection with Discord Gateway
- Automatic session resume and reconnect functionality
- Bot message filtering to prevent response loops
- Direct message conversations with users
- No server setup required - works entirely through DMs

## 🧰 Tools

Nexion supports two kinds of tools:

- Regular tools: Python functions decorated with `@tool` that are auto‑discovered from your project (e.g., `tools.py`, `tools/*.py`, `src/tools.py`). Enable them per‑bot in `bot.yml`.
- MCP tools: Tools discovered from MCP servers defined in `mcp.json`. They are auto‑registered with names like `mcp__<server>__<tool>` and can be enabled per‑bot.

### Regular Tools
- Define functions with `@tool` and type hints; schemas are generated for LLM function calling.
- Example enablement:
  ```yaml
  bots:
    - id: assistant
      tools:
        - add            # custom local tool
  ```

### MCP Tools
- Discovered from MCP servers and registered as `mcp__{server}__{tool}`.
- Example enablement:
  ```yaml
  bots:
    - id: assistant
      tools:
        - mcp__filesystem__read_file
        - mcp__github__get_file_contents
  ```

## 🔗 MCP Integration (Model Context Protocol)

Define MCP servers in an `mcp.json` file at the workspace root. Both stdio and HTTP servers are supported.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "env": {}
    },
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

Notes:
- Env substitution supports:
  - Whole value: `env:VAR`
  - Inline: `Bearer env:VAR` or `Bearer ${env:VAR}` (applies to headers and URL)
  - Also applied to `env` values for stdio servers.
- Some servers return EmbeddedResource items; Nexion automatically calls MCP `read_resource` to fetch and return real content (e.g., GitHub file text).
 - Security: Only configure MCP servers you trust. Avoid arbitrary remote servers from the internet; untrusted tools can read/write files or exfiltrate data. Prefer local or self‑hosted servers and enable the minimum necessary tools.

## 🛠️ CLI Commands

### nexctl

Show help and available commands:

```bash
nexctl                    # Show help
nexctl --help             # Show detailed help
```

### nexctl dev

Run the development server:

```bash
nexctl dev                # Start server on port 8080
nexctl dev --port 3000    # Start server on custom port
```

### nexctl init

Bootstrap a new bot project:

```bash
nexctl init my-bot        # Create new project directory
nexctl init .             # Initialize in current directory
```

Creates:
- `bot.yml` - Basic HTTP bot configuration
- `prompts/system.md` - Friendly system prompt template
- `.env.example` - Environment variable template

## 🧪 Development

### Project Structure

```
my-bot/
├── bot.yml              # Bot configuration
├── .env                 # Environment variables (create from .env.example)
├── prompts/
│   └── system.md        # System prompt
└── .env.example         # Template for environment variables
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | Your OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes* | Your Anthropic API key |
| `BOT_HTTP_KEY` | No | API key for HTTP adapter |
| `TELEGRAM_BOT_TOKEN` | No | Your Telegram bot token |
| `DISCORD_BOT_TOKEN` | No | Your Discord bot token |
| `NEXION_LOG_LEVEL` | No | Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

*At least one LLM provider key is required

### Logging & Troubleshooting

- Set global log level via `log_level` in `bot.yml` or `NEXION_LOG_LEVEL` env (DEBUG, INFO, WARNING, ERROR, CRITICAL).
- MCP diagnostics:
  - INFO logs: tool discovery, content summaries, fetched resource summaries.
  - DEBUG logs: text previews of content where applicable.
- Tool execution is robust: every tool call stores a tool result (success or error) to keep conversation history in order.

### System Prompts

Create custom bot personalities in `prompts/`:

```markdown
You are a helpful customer support assistant for Acme Corp.

Guidelines:
- Always be friendly, professional, and concise
- When you don't know something, say so and offer alternatives
- Focus on solving the customer's problem quickly
- Use a warm, conversational tone
```

## 🔮 Coming Soon

- **📊 Flow Engine**: Visual conversation flows and state management
- **🎯 More Adapters**: Slack, Discord, and other platforms
- **🧠 Knowledge Bases**: Document indexing and retrieval
- **🔧 Tool Integration**: Function calling and external API access
- **📈 Analytics**: Usage metrics and conversation analytics
- **🔐 Advanced Auth**: OAuth, SSO, and role-based access control

## 🚨 Production Notes

- **Change default API keys**: Never use "dev-secret" in production
- **Secure environment variables**: Use proper secret management
- **Rate limiting**: Monitor API usage to avoid hitting provider limits
- **Error handling**: Implement proper logging and monitoring

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE) for details

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Ready to build your AI agent?** Start with `nexctl init my-bot` and you'll be chatting with your custom bot in minutes! 🚀

<!-- Removed duplicate MCP section that was previously appended at the end -->
