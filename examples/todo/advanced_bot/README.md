# Advanced Bot Example

A multi-provider, multi-channel example showcasing both OpenAI and Anthropic models in a single workspace with specialized support and documentation bots.

## 🎯 What This Demonstrates

- **Multi-provider setup**: Both OpenAI and Anthropic providers
- **Specialized bots**: Support bot (OpenAI) + Docs bot (Anthropic)
- **Multi-channel support**: HTTP APIs + Telegram integration
- **Model diversity**: GPT-4o-mini + Claude 3 Sonnet
- **Future architecture preview**: Comments showing planned features

## 🚀 Quick Start

1. **Create a Telegram Bot:**
   - Message @BotFather on Telegram
   - Use `/newbot` command and follow instructions
   - Get your bot token and update bot username in `bot.yml`

2. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and bot token
   ```

3. **Run the bots:**
   ```bash
   nexctl dev --port 8080
   ```

4. **Test all channels:**

   **Support Bot (HTTP):**
   ```bash
   curl -X POST http://localhost:8080/api/chat \
     -H "Authorization: Bearer dev-secret" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user1", "message": "I need help with setup"}'
   ```

   **Docs Bot (HTTP):**
   ```bash
   curl -X POST http://localhost:8080/api/docs-chat \
     -H "Authorization: Bearer dev-secret" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user1", "message": "How do I configure providers?"}'
   ```

   **Support Bot (Telegram):**
   Message your bot directly on Telegram!

5. **Access web UIs:**
   - **Support Bot**: http://localhost:8080/ui/chat
   - **Docs Bot**: http://localhost:8080/ui/docs-chat
   - **Bot navigation**: Switch between bots in the web interface

## 📋 Configuration

- **Support Bot**: OpenAI GPT-4o-mini, HTTP + Telegram channels
- **Docs Bot**: Anthropic Claude 3 Sonnet, HTTP only
- **Authentication**: Shared HTTP API key, separate Telegram bot
- **System Prompts**: Specialized for support vs documentation

## 🔧 Environment Variables

```bash
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
BOT_HTTP_KEY=dev-secret
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

## 🔮 Future Features (Planned)

This example includes commented sections showing planned Nexion features:
- **Flows**: YAML-defined conversation flows (`flows/faq.yml`)
- **Tools**: HTTP callouts and knowledge base search
- **Knowledge Base**: Document ingestion with BM25 search

These features are part of Nexion's roadmap and will be activated in future releases!

Perfect for complex multi-bot deployments! 🚀
