# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

**Install dependencies:**
```bash
uv sync
uv sync --group dev  # Install development dependencies
```

**Set up pre-commit hooks (required for contributors):**
```bash
pre-commit install
```

**Run development server:**
```bash
nexctl dev                # Start server on port 8080
nexctl dev --port 3000    # Start server on custom port
```

**Initialize new bot project:**
```bash
nexctl init my-bot        # Create new project directory
nexctl init .             # Initialize in current directory
```

**Code formatting and linting:**
```bash
ruff check              # Check for linting issues
ruff check --fix        # Auto-fix linting issues
ruff format             # Format code
pre-commit run --all-files  # Run all pre-commit hooks manually
```

**CLI entry point:**
- Main CLI script is at `nexion/cli/nexctl.py`
- Uses Typer for command-line interface
- Entry point defined in `pyproject.toml` as `scripts.nexctl`

## Architecture Overview

Nexion is an AI agent framework for building multi-channel bots via YAML configuration. Currently implements **Phase 1** of the system design with full multi-bot support, dynamic routing, and persistent conversations.

### Current Implementation (Phase 1)

**Core Components:**
- `nexion/core/server.py` - FastAPI server with lifespan management, coordinates all services
- `nexion/core/agent.py` - `AgentRuntime` class handles message processing and LLM provider routing
- `nexion/core/bot_manager.py` - `BotManager` orchestrates multiple bots with dynamic routing
- `nexion/core/types.py` - Shared data types (`MessageEvent`, `Reply`, `ProviderMessage`, etc.)

**Configuration System:**
- `nexion/config/yaml.py` - YAML configuration loader with env variable substitution (`env:VARIABLE_NAME`)
- `nexion/config/settings.py` - Settings management and validation
- `nexion/config/bridge.py` - Bridge between YAML config and runtime settings
- Main config file: `bot.yml` in project root

**Adapters (Channel Interfaces):**
- `nexion/adapters/http.py` - Dynamic HTTP REST APIs and multi-bot web UIs with navigation
- `nexion/adapters/telegram.py` - Telegram bot polling integration
- Each adapter handles channel-specific message formatting and delivery
- HTTP adapter creates individual UIs for each bot with cross-navigation

**LLM Providers:**
- `nexion/providers/openai_.py` - OpenAI integration (Responses API)
- `nexion/providers/anthropic_.py` - Anthropic integration (Claude models)
- `nexion/providers/provider.py` - Base provider interface
- Provider selection based on model prefix in config (e.g., `openai:gpt-5-nano`)
- Support for system prompts via `instructions` field (OpenAI) and message arrays (Anthropic)

**Storage Layer:**
- `nexion/storage/sqlite.py` - SQLite implementation for conversation persistence
- `nexion/storage/models.py` - SQLModel data models for conversations and messages
- `nexion/storage/base.py` - Abstract base classes for storage interfaces
- Automatic database schema initialization and conversation tracking

### Planned Architecture (Full System Design)

**Target Components (Roadmap):**
- **Router & Policy** - Flow engine with YAML-defined conversation flows
- **Tool Registry** - Function calling with Python callables; HTTP via custom tools; MCP integration
- **Knowledge Base** - Markdown ingestion with BM25/embeddings, auto-MCP server generation
- **Additional Adapters** - Slack, Discord with command support
- **Storage Layer** - Postgres for persistence, Redis for caching/queues
- **Observability** - OpenTelemetry tracing, structured logging, token accounting

**Configuration Structure:**
Bot behavior is defined in `bot.yml` with these key sections:
- `bots[]` - Bot instances with channels, models, system prompts, flows, tools
- `providers{}` - LLM API keys and configuration
- `adapters{}` - Channel adapter settings (HTTP, Telegram, Slack, Discord)
- `kb[]` - Knowledge bases with ingestion and indexing
- `flows[]` - Conversation flow definitions (YAML state machines)
 - `log_level` - Optional global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Message Flow (Current):**
1. Channel adapter receives message → normalized `MessageEvent`
2. BotManager routes to appropriate bot based on channel configuration
3. Agent Runtime loads conversation history and system prompt
4. LLM provider processes message with full context
5. Response stored in conversation history
6. Reply sent back through appropriate channel adapter

**Message Flow (Target):**
1. Channel adapter receives message → normalized `MessageEvent`
2. Router applies policies and selects conversation flow
3. Agent Runtime orchestrates: LLM calls, tool calls, KB retrieval
4. Tools/MCP resources provide external data and actions
5. Reply sent back through appropriate channel adapter

## Key File Relationships

- `nexion/cli/nexctl.py` → starts server via `nexion/core/server.py`
- `nexion/core/server.py` → includes HTTP router and starts Telegram polling
- `nexion/config/bridge.py` → loads YAML config and creates runtime settings
- `nexion/core/agent.py` → uses settings to instantiate correct provider
- Adapters communicate with agent runtime through standardized message types

## Development Context

**Current State:** Multi-bot framework with persistent conversations, dynamic routing, and specialized UIs
**Target:** Full agentic platform with tools, flows, knowledge bases, and MCP integration

**System Prompt Handling:**
- Currently: Individual system prompts per bot, loaded from Markdown files, proper OpenAI Responses API integration
- Target: Dynamic prompts with context injection, KB citations, tool schemas

**Configuration Evolution:**
- Current: Basic bot/provider/adapter configuration
- Target: Complex flows, tools, knowledge bases, multi-workspace tenancy

## Development Environment

**Required environment variables:**
- `OPENAI_API_KEY` - For OpenAI models
- `ANTHROPIC_API_KEY` - For Anthropic models
- `BOT_HTTP_KEY` - HTTP adapter authentication (optional)
- `TELEGRAM_BOT_TOKEN` - Telegram bot integration (optional)

**Project uses:**
- Python 3.10+ with uv for dependency management
- FastAPI for HTTP server and REST API
- Typer for CLI interface
- Pydantic for data validation
- YAML configuration with environment variable substitution

## Implementation Notes

When working with this codebase:
- Follow the modular adapter pattern for new channel integrations
- Configuration changes should support both current simple format and planned extended schema
- New features should align with the target architecture (tools, flows, KB, MCP)
- Consider the planned database schema when adding persistence features
- CLI commands should follow the `nexctl` pattern documented in the system design
