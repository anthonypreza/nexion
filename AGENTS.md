# Repository Guidelines

## Project Structure & Module Organization
- `nexion/` — core source code
  - `adapters/` (HTTP, Telegram, Discord), `core/` (agent runtime, server), `providers/` (OpenAI, Anthropic),
    `tools/` (registry, decorators, MCP integration), `storage/` (SQLite + models), `config/` (YAML/.env bridge), `utils/` (logging).
- `examples/` — runnable sample bots (see `examples/discord-bot`, `examples/telegram-bot`).
- Root docs: `README.md`, `CLAUDE.md`, `AGENTS.md` (this file).

## Build, Test, and Development Commands
- Install deps: `uv sync` (add `--group dev` for contributor tooling).
- Run dev server: `nexctl dev` (launches HTTP UI, Telegram polling, and Discord WebSocket if configured).
- Code style (pre-commit): `pre-commit install && pre-commit run -a`.
- Packaging/venv is managed by `uv`; Python 3.10+ recommended.

## Coding Style & Naming Conventions
- Python: 4-space indent, type hints required for new code.
- Naming: modules_snake_case, functions_snake_case, ClassesPascalCase, constants_UPPER.
- Lint/format: Ruff (configured in `pyproject.toml`); run via pre-commit.
- Logging: use `from nexion.utils.logging import get_logger`; avoid printing secrets.

## Testing Guidelines
- No formal test suite yet. Prefer `pytest` with tests in `tests/` named `test_*.py`.
- Keep unit tests small and deterministic; mock network calls.
- Add minimal fixtures for providers/tools when contributing features.

## Commit & Pull Request Guidelines
- Commits: concise, imperative (“Add X”, “Fix Y”); group related changes.
- PRs: clear description, reproduction steps, screenshots/logs when relevant; link issues.
- Keep scope focused; update docs/examples when behavior or configs change.

## Security & Configuration Tips
- Secrets via `.env` and `env:` in `bot.yml`; never commit secrets.
- No built-in generic HTTP tool; create narrow tools (e.g., `fetch_joke`) under `examples/`.
- Logging level: set `log_level` in `bot.yml` or `NEXION_LOG_LEVEL` env.

## MCP Integration
- Define MCP servers in `mcp.json` in the workspace directory. Example:
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
- Env substitution supports `env:VAR`, `${env:VAR}`, and inline `env:VAR` within strings. Applied to stdio `env` values, and HTTP headers/URL.
- MCP tools are auto-registered as `mcp__<server>__<tool>` and can be enabled per-bot via `tools:` in `bot.yml`.
- Embedded resources in MCP responses are fetched via `read_resource` and returned as text when possible (e.g., GitHub file contents).
- Logs include MCP content summaries and fetched resource summaries at INFO (previews at DEBUG).

## Architecture Overview (Brief)
- Provider chosen by `model` prefix (`openai:`/`anthropic:`).
- OpenAI uses the Responses API; Anthropic uses Messages API with tool_use/tool_result.
- Chat-centric conversations persisted in SQLite; conversations keyed by chat/channel ID for persistent context.
- Discord adapter: Full WebSocket integration with resume/reconnect, bot filtering, and session management.
- Telegram adapter: Polling-based with no webhook requirements.
- HTTP adapter: Dynamic REST APIs and multi-bot web interfaces.
