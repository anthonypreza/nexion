# Discord Bot Example

A Discord bot that responds to direct messages sent to your Discord bot.

## 🎯 What This Demonstrates

- **Discord integration**: Bot responds to direct messages
- **WebSocket connection**: Real-time message handling with resume/reconnect
- **Bot filtering**: Ignores messages from other bots to prevent loops
- **Global configuration**: Uses workspace-level provider and adapter settings

## 🚀 Quick Start

1. **Create a Discord Application:**
   - Go to https://discord.com/developers/applications
   - Click "New Application" and give it a name
   - Go to "Bot" section and click "Add Bot"
   - Copy the bot token
   - Under "Privileged Gateway Intents", enable "Message Content Intent"

2. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and Discord bot token
   ```

3. **Run the bot:**
   ```bash
   nexctl dev --port 8080
   ```

4. **Test via Direct Messages:**
   - Find your bot in Discord (it will appear offline initially)
   - Send it a direct message: "Hello!"
   - Bot should respond using GPT-4o-mini

## 📋 Configuration

- **Provider**: OpenAI GPT-4o-mini
- **Channel**: Discord direct messages
- **Authentication**: Uses Discord bot token
- **System Prompt**: Located at `prompts/system.md`

## 🔧 Environment Variables

```bash
OPENAI_API_KEY=sk-your-openai-key-here
DISCORD_BOT_TOKEN=your-discord-bot-token-here
```

## 🤖 Discord Bot Permissions

Your Discord bot needs minimal permissions since it only handles direct messages:
- **Message Content Intent** (required to read message content)
- No server permissions needed for DM-only operation

The bot will automatically connect to Discord's Gateway and handle direct messages when you run `nexctl dev`! 🤖
