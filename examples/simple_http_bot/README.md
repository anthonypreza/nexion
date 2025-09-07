# Simple HTTP Bot Example

A basic HTTP bot that demonstrates the simplest Nexion configuration with a single bot serving HTTP requests.

## 🎯 What This Demonstrates

- **Single HTTP endpoint**: One bot serving `/api/chat`
- **Global configuration**: Uses workspace-level provider and adapter settings
- **Clean configuration**: Minimal setup for quick start

## 🚀 Quick Start

1. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Run the bot:**
   ```bash
   nexctl dev --port 8080
   ```

3. **Test the endpoint:**
   ```bash
   curl -X POST http://localhost:8080/api/chat \
     -H "Authorization: Bearer your-http-key" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user1", "message": "Hello!"}'
   ```

4. **Access web UI:**
   Visit: http://localhost:8080/ui/chat

## 📋 Configuration

- **Provider**: OpenAI GPT-4o-mini
- **Channel**: HTTP endpoint at `/api/chat`
- **Authentication**: Uses global HTTP API key
- **System Prompt**: Located at `prompts/system.md`

## 🔧 Environment Variables

```bash
OPENAI_API_KEY=sk-your-openai-key-here
BOT_HTTP_KEY=your-http-api-key
```

Perfect for getting started with Nexion! 🎉
