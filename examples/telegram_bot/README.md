# Telegram Bot Example

A simple Telegram bot that responds to messages sent to your Telegram bot account.

## 🎯 What This Demonstrates

- **Telegram integration**: Bot responds to direct messages
- **Polling service**: Continuously listens for new messages
- **Global configuration**: Uses workspace-level provider and adapter settings

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

5. **Test on Telegram:**
   - Find your bot on Telegram
   - Send it a message: "Hello!"
   - Bot should respond using GPT-4o-mini

## 📋 Configuration

- **Provider**: OpenAI GPT-4o-mini
- **Channel**: Telegram bot with username `@mybot`
- **Authentication**: Uses Telegram bot token
- **System Prompt**: Located at `prompts/system.md`

## 🔧 Environment Variables

```bash
OPENAI_API_KEY=sk-your-openai-key-here
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

## 📱 Telegram Bot Setup

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Choose a name and username for your bot
4. Copy the bot token to your `.env` file
5. Update the username in `bot.yml`

Your bot will start polling for messages automatically when you run `nexctl dev`! 🤖
