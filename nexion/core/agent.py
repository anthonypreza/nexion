from pathlib import Path

from ..config.settings import BotSettings
from ..core.types import (
    ConversationContext,
    MessageEvent,
    ProviderMessage,
    Reply,
)
from ..providers.anthropic_ import AnthropicProvider
from ..providers.openai_ import OpenAIProvider
from ..storage.base import ConversationStore
from ..storage.sqlite import SQLiteStore
from ..tools.registry import get_tool_registry
from ..utils.logging import get_logger


class AgentRuntime:
    def __init__(self, settings: BotSettings, store: ConversationStore | None = None):
        self.settings = settings
        self.logger = get_logger("agent")

        # Initialize conversation store
        self.store = store or SQLiteStore()

        self.system_prompt = Path(settings.system_prompt_path).read_text(
            encoding="utf-8"
        )

        if settings.openai_api_key and settings.model.startswith("openai"):
            self.provider = OpenAIProvider(
                settings.openai_api_key, max_tokens=settings.max_tokens
            )
            self.model = settings.model.split(":", 1)[1]
            self.logger.info(f"🤖 Using OpenAI provider with model: {self.model}")
        elif settings.anthropic_api_key and settings.model.startswith("anthropic"):
            self.provider = AnthropicProvider(
                settings.anthropic_api_key, max_tokens=settings.max_tokens
            )
            self.model = settings.model.split(":", 1)[1]
            self.logger.info(f"🤖 Using Anthropic provider with model: {self.model}")
        else:
            self.provider = None
            self.model = "echo"
            self.logger.info("🔄 No LLM provider configured, using echo mode")

        self.tool_registry = get_tool_registry()
        self._discover_project_tools()
        self._register_bot_tools(settings.tools)

    def _register_bot_tools(self, tool_names: list[str]):
        """Register tools specified in bot configuration."""
        # Tools are already registered via the tools.__init__ module
        # This method validates that requested tools are available
        available_tools = self.tool_registry.list_tools()

        for tool_name in tool_names:
            if tool_name not in available_tools:
                self.logger.warning(
                    f"⚠️ Tool '{tool_name}' not found. Available tools: {available_tools}"
                )

        # Log registered tools for this bot
        bot_tools = [
            name for name in tool_names if name in self.tool_registry.list_tools()
        ]
        if bot_tools:
            self.logger.info(f"🔧 Bot tools enabled: {bot_tools}")

    def _discover_project_tools(self):
        """Auto-discover and register tools from the user's project directory."""
        import importlib.util
        import os
        import sys
        from pathlib import Path

        # Look for tools in the current working directory
        cwd = Path.cwd()
        tools_files = []

        # Common tool file patterns to look for
        tool_patterns = [
            "tools.py",
            "tools/**/*.py",
            "src/tools.py",
            "src/tools/**/*.py",
        ]

        for pattern in tool_patterns:
            tools_files.extend(cwd.glob(pattern))

        # Also check if there's a tools directory with __init__.py
        tools_dir = cwd / "tools"
        if tools_dir.exists() and (tools_dir / "__init__.py").exists():
            tools_files.append(tools_dir / "__init__.py")

        registered_count = 0
        for tools_file in tools_files:
            if tools_file.is_file() and tools_file.suffix == ".py":
                try:
                    # Convert file path to module name
                    relative_path = tools_file.relative_to(cwd)
                    module_name = str(relative_path.with_suffix("")).replace(
                        os.sep, "."
                    )

                    # Import the module
                    spec = importlib.util.spec_from_file_location(
                        module_name, tools_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)

                        # Register any decorated functions from this module
                        import inspect

                        for _name, obj in inspect.getmembers(
                            module, inspect.isfunction
                        ):
                            if hasattr(obj, "_tool_name"):
                                self.tool_registry.register_function(obj)
                                registered_count += 1

                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Could not import tools from {tools_file}: {e}"
                    )

        if registered_count > 0:
            self.logger.info(
                f"🔧 Auto-discovered {registered_count} custom tools from project files"
            )

    async def _handle_conversation_with_tools(
        self, messages: list[ProviderMessage], tool_schemas: list, conversation_id: str
    ) -> str:
        """Handle multi-turn conversation with tool calling."""
        import json

        def _trunc(text: str, n: int = 300) -> str:
            try:
                s = text if isinstance(text, str) else json.dumps(text)
                return s if len(s) <= n else s[: n - 3] + "..."
            except Exception:
                return str(text)

        max_turns = 5  # Prevent infinite loops
        turn = 0

        while turn < max_turns:
            turn += 1

            # Get response from LLM with tools
            self.logger.info(
                f"🔁 Turn {turn}: request model='{self.model}' with {len(messages)} messages and {len(tool_schemas) if tool_schemas else 0} tools"
            )
            response = await self.provider.chat_with_tools(
                self.model, messages, self.system_prompt, tools=tool_schemas
            )

            # If no tool calls, we're done
            if not response.tool_calls:
                self.logger.info(
                    f"✅ Assistant reply (no tools): {_trunc(response.content)}"
                )
                return response.content

            # Store the assistant's message with tool calls
            # Format depends on provider API expectations
            if isinstance(self.provider, OpenAIProvider):  # OpenAI format
                assistant_message = ProviderMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=[
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                        for tc in response.tool_calls
                    ],
                )
            elif isinstance(self.provider, AnthropicProvider):  # Anthropic format
                # Anthropic expects tool_use blocks inside the assistant content array
                content_blocks = []
                if response.content:
                    content_blocks.append({"type": "text", "text": response.content})
                for tc in response.tool_calls:
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    )
                assistant_message = ProviderMessage(
                    role="assistant", content=content_blocks
                )
            else:
                # Fallback for other providers
                assistant_message = ProviderMessage(
                    role="assistant", content=response.content
                )
            messages.append(assistant_message)
            # Log proposed tool calls
            self.logger.info(
                f"🧠 Assistant proposed {len(response.tool_calls)} tool call(s)"
            )
            for tc in response.tool_calls:
                self.logger.info(
                    f"   • tool={tc.name} id={tc.id} args={_trunc(tc.arguments)}"
                )

            # Store assistant message in conversation
            # For Anthropic, persist the structured content blocks as JSON so we can reconstruct faithfully.
            if isinstance(self.provider, AnthropicProvider):
                import json

                stored_content = (
                    json.dumps(assistant_message.content)
                    if isinstance(assistant_message.content, list)
                    else (assistant_message.content or "")
                )
                await self.store.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=stored_content,
                    metadata={
                        "tool_calls": [tc.__dict__ for tc in response.tool_calls]
                    },
                )
            else:
                await self.store.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response.content,
                    metadata={
                        "tool_calls": [tc.__dict__ for tc in response.tool_calls]
                    },
                )

            # Execute each tool call and create tool result messages
            for tool_call in response.tool_calls:
                # Ensure arguments is a mapping; some providers return JSON strings
                import json as _json

                args = tool_call.arguments
                if isinstance(args, str):
                    try:
                        args = _json.loads(args)
                    except Exception:
                        args = {}
                elif isinstance(args, list):
                    # Normalize list of {name, value} items to a dict
                    norm = {}
                    for item in args:
                        if isinstance(item, dict) and "name" in item:
                            norm[item["name"]] = item.get("value")
                    args = norm
                elif not isinstance(args, dict):
                    args = {}

                self.logger.info(
                    f"🔧 Executing tool '{tool_call.name}' with args={_trunc(args)}"
                )
                result = await self.tool_registry.execute_tool(
                    tool_call.name, **(args or {})
                )
                if result.success:
                    self.logger.info(
                        f"✅ Tool '{tool_call.name}' success: {_trunc(result.result)}"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ Tool '{tool_call.name}' failed: {result.error}"
                    )

                # Create tool result message based on provider type
                if isinstance(self.provider, OpenAIProvider):  # OpenAI format
                    # Do not use role=tool; OpenAI Responses API doesn't accept it in history input
                    tool_result_message = ProviderMessage(
                        role="user",
                        content=f"Tool {tool_call.name} result: {json.dumps(result.dict())}",
                        tool_call_id=tool_call.id,
                    )
                elif isinstance(self.provider, AnthropicProvider):  # Anthropic format
                    tool_result_message = ProviderMessage(
                        role="user",
                        content=[
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call.id,
                                "content": json.dumps(result.dict()),
                            }
                        ],
                    )
                else:
                    # Fallback for other providers
                    tool_result_message = ProviderMessage(
                        role="user",
                        content=f"Tool {tool_call.name} result: {json.dumps(result.dict())}",
                    )

                messages.append(tool_result_message)

                # Store tool result in conversation
                if isinstance(self.provider, AnthropicProvider):
                    # Store the structured tool_result block for Anthropic
                    stored_content = json.dumps(
                        [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call.id,
                                "content": json.dumps(result.dict()),
                            }
                        ]
                    )
                    await self.store.add_message(
                        conversation_id=conversation_id,
                        role="user",
                        content=stored_content,
                        metadata={
                            "tool_call_id": tool_call.id,
                            "tool_name": tool_call.name,
                            "is_tool_result": True,
                        },
                    )
                else:
                    # Store tool results as user messages to avoid unsupported 'tool' role
                    await self.store.add_message(
                        conversation_id=conversation_id,
                        role="user",
                        content=json.dumps(result.dict()),
                        metadata={
                            "tool_call_id": tool_call.id,
                            "tool_name": tool_call.name,
                            "is_tool_result": True,
                        },
                    )

        # If we hit max turns, return the last response
        return (
            "I've reached the maximum number of tool calling turns. Please try again."
        )

    async def initialize(self) -> None:
        """Initialize the agent runtime and storage."""
        await self.store.initialize()
        self.logger.info("🚀 Agent runtime initialized with conversation storage")

    async def handle(self, event: MessageEvent) -> Reply:
        """Handle a message event with conversation context."""

        # Get or create a conversation
        conversation = await self.store.get_or_create_conversation(
            workspace_id=event.workspace_id,
            bot_id=event.bot_id,
            channel_ref=event.channel.value,
            user_ref=event.user_id,
            thread_id=event.thread_id,
        )

        # Store user message
        await self.store.add_message(
            conversation_id=conversation.id,
            role="user",
            content=event.text,
            metadata=event.metadata,
        )

        if not self.provider:
            reply_text = f"(echo) {event.text}"
        else:
            # Get available tool schemas for this bot
            tool_schemas = self.tool_registry.get_tool_schemas(self.settings.tools)

            # Get conversation history
            history = await self.store.get_conversation_history(
                conversation.id, limit=10
            )

            # Build messages for LLM (conversation history only)
            messages = []

            # Add conversation history, reconstructing provider-specific structures
            if isinstance(self.provider, AnthropicProvider):
                for msg in history:
                    meta = msg.message_metadata
                    # Skip OpenAI-only tool role messages
                    if msg.role == "tool":
                        continue
                    # Reconstruct Anthropic tool_result blocks
                    if meta.get("is_tool_result") is True:
                        tool_use_id = meta.get("tool_call_id", "")
                        messages.append(
                            ProviderMessage(
                                role="user",
                                content=[
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_id,
                                        "content": msg.content,
                                    }
                                ],
                            )
                        )
                        continue
                    # Reconstruct assistant tool_use blocks
                    tool_calls = meta.get("tool_calls")
                    if tool_calls:
                        content_blocks = []
                        if msg.content and msg.content.strip():
                            content_blocks.append({"type": "text", "text": msg.content})
                        for tc in tool_calls:
                            content_blocks.append(
                                {
                                    "type": "tool_use",
                                    "id": tc.get("id", ""),
                                    "name": tc.get("name", ""),
                                    "input": tc.get("arguments", {}),
                                }
                            )
                        messages.append(
                            ProviderMessage(role="assistant", content=content_blocks)
                        )
                        continue
                    # Regular conversational message
                    if msg.content and msg.content.strip():
                        messages.append(
                            ProviderMessage(role=msg.role, content=msg.content)
                        )
                    # Otherwise, skip empty messages to satisfy Anthropic requirements
            else:
                for msg in history:
                    messages.append(msg.to_llm_message())

            # Multi-turn tool calling loop
            reply_text = await self._handle_conversation_with_tools(
                messages, tool_schemas, conversation.id
            )

        # Store assistant response
        await self.store.add_message(
            conversation_id=conversation.id, role="assistant", content=reply_text
        )

        return Reply(text=reply_text)

    async def get_conversation_context(
        self, conversation_id: str
    ) -> ConversationContext | None:
        """Get full conversation context for debugging/analysis."""
        conversation = await self.store.get_conversation_by_id(conversation_id)
        if not conversation:
            return None

        history = await self.store.get_conversation_history(conversation.id, limit=50)
        provider_messages = [
            ProviderMessage(role=msg.role, content=msg.content) for msg in history
        ]

        return ConversationContext(
            conversation_id=conversation.id,
            workspace_id=conversation.workspace_id,
            bot_id=conversation.bot_id,
            channel_ref=conversation.channel_ref,
            user_ref=conversation.user_ref,
            thread_id=conversation.thread_id,
            state=conversation.state,
            history=provider_messages,
        )
