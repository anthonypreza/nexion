import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, Tool

from ..utils.logging import get_logger
from .base import BaseTool, ToolResult, ToolSchema

logger = get_logger("mcp")


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    # HTTP MCP server fields
    type: str = "stdio"  # "stdio" or "http"
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class MCPConfig:
    """Configuration for MCP servers from mcp.json."""

    mcp_servers: dict[str, MCPServerConfig] = field(default_factory=dict)


class MCPClient:
    def __init__(self, server_name: str, server_config: MCPServerConfig):
        self.server_name = server_name
        self.server_config = server_config
        self.available_tools: dict[str, Tool] = {}
        self._server_params = None
        self._http_url = None
        self._http_headers = None

    def _process_env_vars(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process environment variable substitution in config data.

        Supports both whole-value form ("env:VAR") and inline forms
        ("${env:VAR}" or "... env:VAR ..."). If an env var is missing in the
        whole-value form, the key is omitted. For inline forms, missing vars are
        replaced with an empty string and a warning is logged.
        """
        processed: dict[str, Any] = {}

        whole_value_pattern = re.compile(r"^env:([A-Za-z_][A-Za-z0-9_]*)$")
        brace_pattern = re.compile(r"\$\{env:([A-Za-z_][A-Za-z0-9_]*)\}")
        inline_pattern = re.compile(r"\benv:([A-Za-z_][A-Za-z0-9_]*)\b")

        def substitute_in_string(s: str) -> str:
            # First replace ${env:VAR}
            def repl_brace(m: re.Match[str]) -> str:
                var = m.group(1)
                val = os.getenv(var)
                if val is None:
                    logger.warning(
                        f"Environment variable {var} not set for MCP server {self.server_name}"
                    )
                    return ""
                return val

            s2 = brace_pattern.sub(repl_brace, s)

            # Then replace bare inline env:VAR tokens
            def repl_inline(m: re.Match[str]) -> str:
                var = m.group(1)
                val = os.getenv(var)
                if val is None:
                    logger.warning(
                        f"Environment variable {var} not set for MCP server {self.server_name}"
                    )
                    return ""
                return val

            return inline_pattern.sub(repl_inline, s2)

        for key, value in data.items():
            if isinstance(value, str):
                # Whole-value form env:VAR
                m = whole_value_pattern.match(value.strip())
                if m:
                    env_var = m.group(1)
                    env_value = os.getenv(env_var)
                    if env_value is None:
                        logger.warning(
                            f"Environment variable {env_var} not set for MCP server {self.server_name}"
                        )
                        # Skip this key entirely (preserves previous behavior for env dict)
                        continue
                    processed[key] = env_value
                else:
                    # Inline substitution within strings
                    processed[key] = substitute_in_string(value)
            elif isinstance(value, dict):
                processed[key] = self._process_env_vars(value)
            elif isinstance(value, list):
                processed[key] = [
                    substitute_in_string(v) if isinstance(v, str) else v for v in value
                ]
            else:
                processed[key] = value
        return processed

    async def discover_tools(self):
        """Discover available tools from the MCP server."""
        logger.info(
            f"Discovering tools from MCP server '{self.server_name}' (type: {self.server_config.type})..."
        )

        if self.server_config.type == "http":
            await self._discover_tools_http()
        else:
            await self._discover_tools_stdio()

    async def _discover_tools_stdio(self):
        """Discover tools from stdio MCP server."""
        # Process environment variables in server config
        processed_env = self._process_env_vars(self.server_config.env)

        # Create and store server parameters for later use
        self._server_params = StdioServerParameters(
            command=self.server_config.command,
            args=self.server_config.args,
            env=processed_env,
        )

        logger.debug(
            f"MCP server '{self.server_name}' command: {self._server_params.command} {' '.join(self._server_params.args)}"
        )

        # Use proper async context managers - exactly like the official docs
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                logger.debug(
                    f"Initializing MCP session for server '{self.server_name}'..."
                )
                await session.initialize()

                # List and cache available tools
                logger.debug(f"Listing tools for MCP server '{self.server_name}'...")
                response = await session.list_tools()
                self.available_tools = {tool.name: tool for tool in response.tools}

                logger.info(
                    f"✅ Discovered tools from MCP server '{self.server_name}': {list(self.available_tools.keys())}"
                )

    async def _discover_tools_http(self):
        """Discover tools from HTTP MCP server."""
        # Process environment variables in headers and URL
        processed_headers = self._process_env_vars(self.server_config.headers)
        processed_url = self.server_config.url
        if isinstance(processed_url, str):
            # Reuse the same substitution logic used for dict values
            processed_url = self._process_env_vars({"_u": processed_url}).get(
                "_u", processed_url
            )

        # Store for later use
        self._http_url = processed_url
        self._http_headers = processed_headers

        logger.debug(f"MCP server '{self.server_name}' URL: {self._http_url}")

        # Connect to HTTP MCP server
        async with streamablehttp_client(
            self._http_url, headers=self._http_headers
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                logger.debug(
                    f"Initializing HTTP MCP session for server '{self.server_name}'..."
                )
                await session.initialize()

                # List and cache available tools
                logger.debug(
                    f"Listing tools for HTTP MCP server '{self.server_name}'..."
                )
                response = await session.list_tools()
                self.available_tools = {tool.name: tool for tool in response.tools}

                logger.info(
                    f"✅ Discovered tools from HTTP MCP server '{self.server_name}': {list(self.available_tools.keys())}"
                )

    async def execute_tool(
        self, tool_name: str, tool_args: dict[str, Any]
    ) -> CallToolResult:
        """Execute a tool on the MCP server by creating a fresh connection."""
        logger.debug(
            f"Executing MCP tool {self.server_name}.{tool_name} with args {tool_args}"
        )

        if self.server_config.type == "http":
            return await self._execute_tool_http(tool_name, tool_args)
        else:
            return await self._execute_tool_stdio(tool_name, tool_args)

    async def _execute_tool_stdio(
        self, tool_name: str, tool_args: dict[str, Any]
    ) -> CallToolResult:
        """Execute tool on stdio MCP server."""
        if not self._server_params:
            raise RuntimeError(
                f"MCP stdio client for server '{self.server_name}' not initialized"
            )

        # Create a fresh connection for each tool execution
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, tool_args)
                logger.debug(
                    f"MCP tool {self.server_name}.{tool_name} execution completed"
                )
                return result

    async def _execute_tool_http(
        self, tool_name: str, tool_args: dict[str, Any]
    ) -> CallToolResult:
        """Execute tool on HTTP MCP server."""
        if not self._http_url:
            raise RuntimeError(
                f"MCP HTTP client for server '{self.server_name}' not initialized"
            )

        # Create a fresh connection for each tool execution
        async with streamablehttp_client(
            self._http_url, headers=self._http_headers
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, tool_args)
                logger.debug(
                    f"MCP HTTP tool {self.server_name}.{tool_name} execution completed"
                )
                return result

    async def read_resource(self, uri: str) -> Any:
        """Read a resource from the MCP server given its URI.

        Opens a short-lived session to fetch the resource using the appropriate
        transport (stdio or http).
        """
        if self.server_config.type == "http":
            if not self._http_url:
                raise RuntimeError(
                    f"MCP HTTP client for server '{self.server_name}' not initialized"
                )
            async with streamablehttp_client(
                self._http_url, headers=self._http_headers
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.read_resource(uri)
        else:
            if not self._server_params:
                raise RuntimeError(
                    f"MCP stdio client for server '{self.server_name}' not initialized"
                )
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.read_resource(uri)


class MCPTool(BaseTool):
    """Wrapper tool that bridges MCP tools with Nexion's tool registry."""

    def __init__(self, client: MCPClient, tool_name: str, mcp_tool: Tool):
        # Create a name in the format mcp__<server_name>__<tool_name>
        nexion_tool_name = f"mcp__{client.server_name}__{tool_name}"
        super().__init__(
            nexion_tool_name, mcp_tool.description or f"MCP tool {tool_name}"
        )

        self.client = client
        self.mcp_tool_name = tool_name
        self.mcp_tool = mcp_tool

    def get_schema(self) -> ToolSchema:
        """Convert MCP tool schema to Nexion tool schema."""
        # Convert MCP tool input schema to Nexion format
        parameters = {"type": "object", "properties": {}, "required": []}

        if self.mcp_tool.inputSchema:
            input_schema = self.mcp_tool.inputSchema
            if isinstance(input_schema, dict):
                # Handle JSON Schema format
                if "properties" in input_schema:
                    parameters["properties"] = input_schema["properties"]
                if "required" in input_schema:
                    parameters["required"] = input_schema["required"]

        return ToolSchema(
            name=self.name, description=self.description, parameters=parameters
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the MCP tool."""
        try:
            result = await self.client.execute_tool(self.mcp_tool_name, kwargs)

            # Convert MCP result to Nexion result
            if result.isError:
                # Log detailed MCP error result
                try:
                    raw_dict = (
                        result.model_dump()  # pydantic v2
                        if hasattr(result, "model_dump")
                        else (result.dict() if hasattr(result, "dict") else None)
                    )
                except Exception:
                    raw_dict = None
                if raw_dict is None:
                    try:
                        raw_dict = {
                            k: v
                            for k, v in result.__dict__.items()
                            if not callable(v) and not k.startswith("__")
                        }
                    except Exception:
                        raw_dict = {"repr": repr(result)}
                logger.info(
                    f"MCP tool {self.client.server_name}.{self.mcp_tool_name} returned error; raw={raw_dict}"
                )
                return ToolResult(
                    success=False,
                    error=f"MCP tool error: {result.content[0].text if result.content else 'Unknown error'}",
                )

            # Extract content from MCP result
            content_summaries = []
            content = []
            resource_texts: list[Any] = []
            fetched_resource_summaries: list[dict] = []

            def _summarize_item(item: Any) -> dict:
                summary: dict[str, Any] = {"class": type(item).__name__}
                for attr in ("type", "mimeType", "encoding", "uri", "name", "format"):
                    if hasattr(item, attr):
                        summary[attr] = getattr(item, attr)
                if hasattr(item, "text"):
                    text_val = item.text
                    try:
                        summary["text_len"] = (
                            len(text_val) if text_val is not None else 0
                        )
                    except Exception:
                        summary["text_len"] = None
                if hasattr(item, "data"):
                    data_val = item.data
                    try:
                        summary["data_len"] = (
                            len(data_val) if data_val is not None else 0
                        )
                    except Exception:
                        summary["data_len"] = None
                return summary

            for item in result.content:
                content_summaries.append(_summarize_item(item))
                if hasattr(item, "text"):
                    content.append(item.text)
                    continue
                if hasattr(item, "data"):
                    content.append(item.data)
                    continue
                # If the item is an EmbeddedResource, fetch it
                if hasattr(item, "resource") and item.resource is not None:
                    uri = (
                        getattr(item.resource, "uri", None)
                        if hasattr(item, "resource")
                        else None
                    )
                    if uri:
                        try:
                            read_result = await self.client.read_resource(uri)
                            fetched_summaries = []
                            for rc in getattr(read_result, "contents", []) or []:
                                fetched_summaries.append(_summarize_item(rc))
                                if hasattr(rc, "text") and rc.text is not None:
                                    content.append(rc.text)
                                    resource_texts.append(rc.text)
                                elif hasattr(rc, "blob") and rc.blob is not None:
                                    # Attempt decode if text/*, else return raw blob
                                    try:
                                        mt = getattr(rc, "mimeType", "") or ""
                                        if isinstance(
                                            rc.blob, bytes | bytearray
                                        ) and mt.startswith("text/"):
                                            decoded = rc.blob.decode(
                                                "utf-8", errors="replace"
                                            )
                                            content.append(decoded)
                                            resource_texts.append(decoded)
                                        else:
                                            content.append(rc.blob)
                                    except Exception:
                                        content.append(rc.blob)
                            if fetched_summaries:
                                logger.info(
                                    f"MCP tool {self.client.server_name}.{self.mcp_tool_name} fetched resource {uri} summary: {fetched_summaries}"
                                )
                                fetched_resource_summaries.append(
                                    {"uri": uri, "contents": fetched_summaries}
                                )
                        except Exception as fe:
                            logger.warning(
                                f"Failed to fetch MCP resource at {uri}: {fe}"
                            )

            # Log comprehensive but safe details about the MCP result
            logger.info(
                f"MCP tool {self.client.server_name}.{self.mcp_tool_name} content summary: {content_summaries}"
            )
            # Add deeper preview at debug level
            try:
                previews = []
                for item in result.content:
                    if hasattr(item, "text") and isinstance(item.text, str):
                        previews.append(
                            {
                                "class": type(item).__name__,
                                "text_preview": (item.text[:200] + "...")
                                if len(item.text) > 200
                                else item.text,
                            }
                        )
                if previews:
                    logger.debug(
                        f"MCP tool {self.client.server_name}.{self.mcp_tool_name} text previews: {previews}"
                    )
            except Exception:
                pass

            # Prefer fetched resource text if present; otherwise return combined content
            if resource_texts:
                result_payload: Any = (
                    resource_texts[0] if len(resource_texts) == 1 else resource_texts
                )
            else:
                result_payload = content[0] if len(content) == 1 else content

            return ToolResult(
                success=True,
                result=result_payload,
                metadata={
                    "server": self.client.server_name,
                    "tool": self.mcp_tool_name,
                    "raw_content_summary": content_summaries,
                    "fetched_resources": fetched_resource_summaries,
                },
            )

        except Exception as e:
            logger.error(f"Error executing MCP tool {self.name}: {e}")
            return ToolResult(
                success=False, error=f"MCP tool execution failed: {str(e)}"
            )


class MCPManager:
    """Manages MCP server connections and tool registration."""

    def __init__(self, tool_registry):
        from .registry import ToolRegistry

        self.tool_registry: ToolRegistry = tool_registry
        self.clients: dict[str, MCPClient] = {}
        self.logger = logger

    async def initialize_mcp_tools(self, config_path: Path):
        """Load MCP configuration and register tools with the tool registry."""
        self.logger.info(f"🔌 Initializing MCP tools from {config_path}")

        config = load_mcp_config(config_path)

        if not config.mcp_servers:
            self.logger.info("No MCP servers configured in mcp.json")
            return

        self.logger.info(
            f"Found {len(config.mcp_servers)} MCP servers to connect: {list(config.mcp_servers.keys())}"
        )

        # Connect to each server and register its tools
        total_tools = 0
        successful_connections = 0

        for server_name, server_config in config.mcp_servers.items():
            try:
                tools_count = await self._connect_server(server_name, server_config)
                total_tools += tools_count
                successful_connections += 1
            except Exception as e:
                self.logger.error(
                    f"❌ Failed to connect to MCP server '{server_name}': {e}"
                )
                # Don't re-raise, continue with other servers
                continue

        if successful_connections > 0:
            self.logger.info(
                f"🎉 MCP initialization complete: {successful_connections}/{len(config.mcp_servers)} servers connected, {total_tools} total tools registered"
            )
        else:
            self.logger.warning("⚠️ No MCP servers could be connected")

    async def _connect_server(
        self, server_name: str, server_config: MCPServerConfig
    ) -> int:
        """Connect to a single MCP server and register its tools. Returns number of tools registered."""
        self.logger.info(f"🔗 Discovering tools from MCP server '{server_name}'...")

        client = MCPClient(server_name, server_config)

        try:
            await client.discover_tools()
            self.clients[server_name] = client

            # Register all tools from this server
            tools_registered = 0
            self.logger.debug(
                f"Registering {len(client.available_tools)} tools from server '{server_name}'"
            )

            for tool_name, mcp_tool in client.available_tools.items():
                try:
                    wrapper_tool = MCPTool(client, tool_name, mcp_tool)
                    self.tool_registry.register_tool(wrapper_tool)
                    tools_registered += 1
                    self.logger.debug(f"✅ Registered MCP tool: {wrapper_tool.name}")
                except Exception as e:
                    self.logger.error(
                        f"❌ Failed to register tool '{tool_name}' from server '{server_name}': {e}"
                    )
                    continue

            if tools_registered > 0:
                self.logger.info(
                    f"✅ MCP server '{server_name}' initialized with {tools_registered} tools registered"
                )
            else:
                self.logger.warning(
                    f"⚠️ MCP server '{server_name}' initialized but no tools were registered"
                )

            return tools_registered

        except Exception as e:
            self.logger.error(
                f"❌ Failed to initialize MCP server '{server_name}': {type(e).__name__}: {e}"
            )
            # Clean up failed client
            if server_name in self.clients:
                del self.clients[server_name]
            raise

    async def shutdown(self):
        """Clean up all MCP client connections."""
        # No persistent connections to clean up in the new model
        self.clients.clear()
        self.logger.info("MCP manager shutdown complete")


def load_mcp_config(config_path: Path) -> MCPConfig:
    """Load MCP configuration from mcp.json file."""
    if not config_path.exists():
        logger.debug(f"MCP config file not found: {config_path}")
        return MCPConfig()

    try:
        with open(config_path) as f:
            raw_config = json.load(f)

        # Process the configuration
        servers = {}
        if "mcpServers" in raw_config:
            for server_name, server_data in raw_config["mcpServers"].items():
                server_type = server_data.get("type", "stdio")

                if server_type == "http":
                    servers[server_name] = MCPServerConfig(
                        name=server_name,
                        type="http",
                        url=server_data.get("url", ""),
                        headers=server_data.get("headers", {}),
                    )
                else:
                    # Default to stdio
                    servers[server_name] = MCPServerConfig(
                        name=server_name,
                        type="stdio",
                        command=server_data.get("command", ""),
                        args=server_data.get("args", []),
                        env=server_data.get("env", {}),
                    )

        config = MCPConfig(mcp_servers=servers)
        logger.info(
            f"Loaded MCP configuration with {len(config.mcp_servers)} servers: {list(config.mcp_servers.keys())}"
        )
        return config

    except Exception as e:
        logger.error(f"Failed to load MCP config from {config_path}: {e}")
        return MCPConfig()
