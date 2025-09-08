# Multiple HTTP Bots Example

Deploy multiple specialized bots serving different HTTP endpoints, each with their own purpose and system prompts.

## 🎯 What This Demonstrates

- **Multiple bots**: Two different bots with distinct personalities
- **Route-specific endpoints**: FAQ bot at `/api/faq/chat`, Sales bot at `/api/sales/chat`
- **Specialized system prompts**: Each bot optimized for its specific role
- **Shared authentication**: Single API key for all bots
- **Multi-bot web UI**: Navigate between bots in the web interface

## 🚀 Quick Start

1. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

2. **Run the bots:**
   ```bash
   nexctl dev --port 8080
   ```

3. **Test the endpoints:**

   **FAQ Bot:**
   ```bash
   curl -X POST http://localhost:8080/api/faq/chat \
     -H "Authorization: Bearer dev-secret" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user1", "message": "What is Nexion?"}'
   ```

   **Sales Bot:**
   ```bash
   curl -X POST http://localhost:8080/api/sales/chat \
     -H "Authorization: Bearer dev-secret" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user1", "message": "Why should I use Nexion?"}'
   ```

4. **Access web UIs:**
   - **FAQ Bot**: http://localhost:8080/ui/faq/chat
   - **Sales Bot**: http://localhost:8080/ui/sales/chat
   - **Navigation**: Use the bot selector to switch between bots

## 📋 Configuration

- **Bots**: FAQ Assistant + Sales Assistant
- **Provider**: OpenAI GPT-4o-mini (shared)
- **Channels**: Separate HTTP endpoints per bot
- **Authentication**: Shared HTTP API key
- **System Prompts**:
  - `prompts/faq.md` - Technical Q&A specialist
  - `prompts/sales.md` - Business value specialist

## 🔧 Environment Variables

```bash
OPENAI_API_KEY=sk-your-openai-key-here
BOT_HTTP_KEY=dev-secret
```

## 🤖 Bot Personalities

**FAQ Bot** (`/api/faq/chat`):
- Answers technical questions about Nexion
- Helps with setup and troubleshooting
- Provides framework documentation

**Sales Bot** (`/api/sales/chat`):
- Explains business value and use cases
- Helps with adoption decisions
- Focuses on ROI and benefits

Perfect for building specialized bot teams! 🎯
