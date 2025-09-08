# Nexion MCP Example (Security-Focused)

This example demonstrates how to use Model Context Protocol (MCP) servers with Nexion bots in a security-conscious way, providing read-only access to filesystem and GitHub repositories.

## Quick Start

1. **Configure MCP servers** in `mcp.json`:
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

2. **Enable read-only MCP tools** in your `bot.yml`:
```yaml
bots:
  - id: filesystem-bot
    tools:
      - mcp__filesystem__read_file      # Read files from /tmp (secure)
      - mcp__github__get_file_contents  # Read GitHub files (secure)
```

3. **Start the bot**:
```bash
nexctl dev
```

The MCP servers will be automatically discovered and their tools made available to your bot.

## How MCP Works

Nexion supports the Model Context Protocol (MCP), which allows AI assistants to securely interact with external systems through standardized server interfaces.

- **MCP Server Discovery**: Nexion automatically connects to MCP servers defined in `mcp.json`
- **Tool Registration**: MCP tools are automatically registered with names like `mcp__<server>__<tool>`
- **Secure Execution**: Each MCP tool execution creates a fresh connection to the server
- **JSON Schema Integration**: MCP tool schemas are converted for LLM function calling

## File Structure

```
mcp-example/
├── bot.yml           # Bot configuration with MCP tools
├── mcp.json          # MCP server configurations
├── .env.example      # Environment variables template
└── prompts/
    └── system.md     # System prompt for the MCP-enabled bot
```

## Security-Focused MCP Configuration

This example demonstrates security best practices by:

- **Read-Only Access**: Only read operations are enabled for security
- **Limited Scope**: Filesystem access restricted to /tmp directory
- **Principle of Least Privilege**: Bot only has access to necessary tools

### Configured MCP Servers:

- **Filesystem Server (stdio)**: Read files from /tmp directory only
  - `mcp__filesystem__read_file` - Read file contents (read-only)

- **GitHub Server (HTTP)**: Read repository files
  - `mcp__github__get_file_contents` - Read GitHub repository files (read-only)

### Security Notes:

- Write operations (`write_file`, `create_file`) are intentionally excluded
- Directory traversal is limited to /tmp scope for filesystem operations
- GitHub access is read-only to prevent unauthorized repository modifications

## Configuring MCP Servers

Add servers to `mcp.json`:

### Stdio MCP Servers (default)
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "env": {}
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "env:GITHUB_TOKEN"
      }
    }
  }
}
```

### HTTP MCP Servers
```json
{
  "mcpServers": {
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

Environment variables in MCP configuration use the `env:` prefix to reference actual environment variables. You can use either whole-value (`env:VAR`) or inline forms (`Bearer env:VAR` or `Bearer ${env:VAR}`) inside strings. HTTP MCP servers support headers for authentication and URL templating.

When an MCP tool returns an embedded resource (e.g., GitHub `get_file_contents`), Nexion will automatically fetch the referenced resource via MCP `read_resource` and return the actual content (e.g., file text) to your bot.

## Testing

Run the MCP example:
```bash
cd examples/mcp-example
nexctl dev           # Starts the bot with MCP tools
```

Chat with your bot and try:
- "Read the contents of a file in /tmp" - ✅ Allowed (read-only)
- "Get the contents of a GitHub repository file" - ✅ Allowed (read-only)
- "Write a test file with some content" - ❌ Not allowed (write operation excluded for security)

The bot will use only the configured read-only MCP tools, demonstrating secure MCP integration with Nexion.
