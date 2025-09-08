# HTTP and Telegram Bot Example

A dual-channel bot that serves both HTTP API requests and Telegram messages using a single bot configuration.

## 🎯 What This Demonstrates

- **Multi-channel bot**: Single bot serving both HTTP and Telegram
- **Unified conversations**: Same conversation context across both channels
- **Global configuration**: Shared provider and adapter settings
- **Channel switching**: Users can interact via web UI or Telegram seamlessly

## 🚀 Quick Start

1. **Create a Telegram Bot:**
   - Message @BotFather on Telegram
   - Use `/newbot` command and follow instructions
   - Get your bot token (looks like `1234567890:ABC-DEF1234ghIkl...`)
   - Note your bot's username (e.g., `@mybot`)

2. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and bot token
   ```

3. **Update bot username:**
   Edit `bot.yml` and change `@mybot` to your actual bot username

4. **Run the bot:**
   ```bash
   nexctl dev --port 8080
   ```

5. **Test both channels:**
   - **HTTP**: Visit http://localhost:8080/ui/chat or use curl
   - **Telegram**: Find your bot and send a message
   - Same conversation context across both!

## 📋 Configuration

- **Provider**: OpenAI GPT-4o-mini
- **Channels**: HTTP endpoint `/api/chat` + Telegram bot
- **Authentication**: HTTP uses API key, Telegram uses bot token
- **System Prompt**: Located at `prompts/system.md`

## 🔧 Environment Variables

```bash
OPENAI_API_KEY=sk-your-openai-key-here
BOT_HTTP_KEY=dev-secret
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

## 🌐 Usage Examples

**HTTP API:**
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1", "message": "Hello from HTTP!"}'
```

**Telegram:**
Just message your bot directly on Telegram!

Perfect for building bots that serve multiple user preferences! 🤖📱
