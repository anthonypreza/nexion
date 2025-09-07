# Multi-Tenant Bot Configuration Example

This example demonstrates the advanced multi-bot configuration capabilities of Nexion, showcasing how to run multiple bots with isolated credentials, different LLM providers, and separate API endpoints.

## 🌟 Features Demonstrated

### ✅ **Per-Bot Credentials**
- Each bot can use different API keys for LLM providers
- Separate HTTP API keys for different endpoints
- Independent Telegram bot tokens
- Fallback to global credentials when not specified

### ✅ **Mixed Configuration Formats**
- New structured channel format with embedded adapter configs
- Legacy flat channel strings (backward compatibility)
- Mixed usage within the same configuration file

### ✅ **Multi-Provider Support**
- Support bot uses Anthropic Claude with custom credentials
- Sales bot uses OpenAI GPT-4 with separate billing
- Dev bot uses global OpenAI credentials as fallback
- HR bot mixes custom and global configurations

### ✅ **Security Isolation**
- Each department gets isolated API access
- Support team can't access sales API keys
- HR data remains on separate credentials
- Demo bot uses public/shared resources

## 🏗️ Architecture

```mermaid
graph TB
    A[bot.yml] --> B[BotManager]
    B --> C[support_bot]
    B --> D[sales_bot]
    B --> E[dev_bot]
    B --> F[hr_bot]
    B --> G[demo_bot]

    C --> C1[Anthropic + Custom Keys]
    C --> C2[HTTP /api/support]
    C --> C3[Telegram @supportbot]

    D --> D1[OpenAI + Custom Keys]
    D --> D2[HTTP /api/sales]
    D --> D3[Telegram @salesbot]

    E --> E1[OpenAI + Global Keys]
    E --> E2[HTTP /api/dev]
    E --> E3[Telegram @devbot]

    F --> F1[Anthropic + Custom Keys]
    F --> F2[HTTP /api/hr]
    F --> F3[Telegram @hrbot]

    G --> G1[OpenAI + Global Keys]
    G --> G2[HTTP /api/demo]
```

## 🚀 Setup Instructions

### 1. **Environment Configuration**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual API keys and tokens
nano .env
```

### 2. **Install Dependencies**
```bash
# From the project root
uv sync
uv sync --group dev
```

### 3. **Run the Multi-Bot Server**
```bash
# From this example directory
nexctl dev --port 8080
```

### 4. **Test the Endpoints**

#### **HTTP API Endpoints**
Each bot has its own HTTP endpoint with isolated authentication:

```bash
# Support Bot (uses SUPPORT_HTTP_API_KEY)
curl -X POST http://localhost:8080/api/support \\
  -H "Authorization: Bearer SUPPORT_HTTP_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "customer1", "message": "I need help with login issues"}'

# Sales Bot (uses SALES_HTTP_API_KEY)
curl -X POST http://localhost:8080/api/sales \\
  -H "Authorization: Bearer SALES_HTTP_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "lead1", "message": "Tell me about your enterprise solution"}'

# Dev Bot (uses DEFAULT_HTTP_API_KEY)
curl -X POST http://localhost:8080/api/dev \\
  -H "Authorization: Bearer DEFAULT_HTTP_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "dev1", "message": "How do I authenticate with your API?"}'

# HR Bot (uses HR_HTTP_API_KEY)
curl -X POST http://localhost:8080/api/hr \\
  -H "Authorization: Bearer HR_HTTP_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "employee1", "message": "What are our vacation policies?"}'

# Demo Bot (uses DEFAULT_HTTP_API_KEY, public access)
curl -X POST http://localhost:8080/api/demo \\
  -H "Authorization: Bearer DEFAULT_HTTP_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "visitor1", "message": "Show me what your AI can do!"}'
```

#### **Web UI Access**
- Support: http://localhost:8080/ui/support
- Sales: http://localhost:8080/ui/sales
- Dev: http://localhost:8080/ui/dev
- HR: http://localhost:8080/ui/hr
- Demo: http://localhost:8080/ui/demo

#### **Telegram Bots**
Each Telegram bot runs independently with its own token:
- @supportbot (SUPPORT_TELEGRAM_BOT_TOKEN)
- @salesbot (SALES_TELEGRAM_BOT_TOKEN)
- @devbot (DEFAULT_TELEGRAM_BOT_TOKEN)
- @hrbot (DEFAULT_TELEGRAM_BOT_TOKEN)

## 📋 Configuration Reference

### **New Channel Format**
```yaml
channels:
  - channel: "http:/api/endpoint"
    adapter_config:
      api_key: "env:CUSTOM_HTTP_KEY"
  - channel: "telegram:@botusername"
    adapter_config:
      bot_token: "env:CUSTOM_TELEGRAM_TOKEN"
```

### **Legacy Format (Still Supported)**
```yaml
channels:
  - "http:/api/endpoint"  # Uses global HTTP key
  - "telegram:@botusername"  # Uses global Telegram token
```

### **Provider Overrides**
```yaml
provider_config:
  openai:
    api_key: "env:BOT_SPECIFIC_OPENAI_KEY"
    max_tokens: 2048
  anthropic:
    api_key: "env:BOT_SPECIFIC_ANTHROPIC_KEY"
    max_tokens: 1500
```

## 🔐 Security Best Practices

1. **Credential Isolation**: Each team/bot uses separate API keys
2. **Least Privilege**: Bots only have access to their required resources
3. **Environment Variables**: All secrets stored in environment variables
4. **Key Rotation**: Easy to rotate individual bot credentials without affecting others
5. **Audit Trail**: Each API key maps to specific functionality for better monitoring

## 🔄 Migration Path

### **From Single Bot**
1. Keep existing global configurations as fallbacks
2. Add new bots with specific configurations
3. Gradually migrate existing bots to use isolated credentials

### **From Legacy Configuration**
1. Existing configurations work unchanged
2. Add new channel configurations using structured format
3. Mix old and new formats as needed during transition

## 📈 Use Cases

- **Enterprise Departments**: Each department gets isolated AI resources
- **Multi-Client Agencies**: Separate clients get separate billing/credentials
- **Development Stages**: Dev, staging, production bots with different configs
- **A/B Testing**: Different bot configurations for testing variations
- **Compliance**: Sensitive data handling with isolated credentials

This example showcases the full power of Nexion's multi-tenant architecture! 🎉
