# Nexion

> An open-source AI agent framework for building bots that can be deployed across multiple channels

Nexion lets you build AI-powered bots using simple YAML configuration and deploy them to HTTP endpoints and Telegram. Perfect for creating support bots, documentation assistants, and interactive AI experiences.

## ✨ Current Features

- **🤖 Multi-LLM Support**: OpenAI (Responses API) and Anthropic integration with your API keys
- **🌐 Dynamic HTTP Interfaces**: Multiple bots with individual web UIs and REST APIs
- **🎯 Multi-Bot Architecture**: Run multiple specialized bots from a single configuration
- **📱 Telegram Integration**: Connect to Telegram bots via polling (no webhooks needed)
- **💾 Persistent Conversations**: SQLite-based conversation history and context
- **📝 YAML Configuration**: Simple, declarative bot configuration with environment variable support
- **🔧 CLI Tools**: Bootstrap projects and run development servers
- **🎨 Custom System Prompts**: Personalize each bot's personality and behavior
- **🔄 Pre-commit Hooks**: Automated code formatting with Ruff

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

**Examples:**
```yaml
channels:
  - "http:/api/chat"        # HTTP endpoint
  - "telegram:@supportbot"  # Telegram bot
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

**OpenAI Models:**
- `openai:gpt-4o-mini` (default)
- `openai:gpt-4o`
- `openai:gpt-5-nano` (latest GPT-5 model)
- `openai:gpt-3.5-turbo`

**Anthropic Models:**
- `anthropic:claude-3-haiku`
- `anthropic:claude-3-sonnet`
- `anthropic:claude-3-opus`

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
    model: openai:gpt-5-nano
  - id: sales-bot
    channels: ["http:/api/sales/chat"]
    system_prompt: prompts/sales.md
    model: openai:gpt-4o

providers:
  openai:
    api_key: env:OPENAI_API_KEY

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

The Telegram adapter uses polling mode (no webhooks required):

**Setup:**
1. Create a bot with @BotFather on Telegram
2. Get your bot token
3. Set `TELEGRAM_BOT_TOKEN` environment variable
4. Configure channels with `telegram:@yourbotname`

**Features:**
- Automatic polling startup when token is configured
- No webhook setup required - perfect for local development
- Direct message support

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
| `NEXION_LOG_LEVEL` | No | Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

*At least one LLM provider key is required

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
