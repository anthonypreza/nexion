from collections.abc import Callable

from ..utils.logging import get_logger
from .base import BaseTool, ToolResult, ToolSchema


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._functions: dict[str, Callable] = {}
        self.logger = get_logger("tools")

    def register_tool(self, tool_instance: BaseTool):
        """Register a new tool."""
        self._tools[tool_instance.name] = tool_instance
        self.logger.debug(
            f"Registered tool: {tool_instance.name} ({type(tool_instance).__name__})"
        )

    def register_function(self, func: Callable):
        """Register a decorated function as a tool."""
        if not hasattr(func, "_tool_name"):
            raise ValueError(f"Function {func.__name__} not decorated with @tool")
        self._functions[func._tool_name] = func

    def get_tool_schemas(self, tool_names: list[str] = None) -> list[ToolSchema]:
        """Get JSON schemas for LLM function calling."""
        schemas = []

        # If no specific tools requested, return all
        if tool_names is None:
            tool_names = self.list_tools()

        for tool_name in tool_names:
            # Check BaseTool instances first
            if tool_name in self._tools:
                schemas.append(self._tools[tool_name].get_schema())
            # Check decorated functions
            elif tool_name in self._functions:
                func = self._functions[tool_name]
                schemas.append(func._tool_schema)

        return schemas

    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name with arguments."""
        try:
            self.logger.info(f"🔧 Running tool '{name}' with args={kwargs}")
            # Check BaseTool instances first
            if name in self._tools:
                res = await self._tools[name].execute(**kwargs)
                self.logger.info(
                    f"✅ Tool '{name}' result: {res.result if res.success else res.error}"
                )
                return res

            # Check decorated functions
            elif name in self._functions:
                func = self._functions[name]

                # Execute function (handle both sync and async)
                import asyncio

                if asyncio.iscoroutinefunction(func):
                    result = await func(**kwargs)
                else:
                    result = func(**kwargs)

                res = ToolResult(success=True, result=result)
                self.logger.info(f"✅ Tool '{name}' result: {result}")
                return res

            else:
                res = ToolResult(
                    success=False,
                    error=f"Tool '{name}' not found. Available tools: {self.list_tools()}",
                )
                self.logger.warning(res.error)
                return res

        except Exception as e:
            err = f"Error executing tool '{name}': {str(e)}"
            self.logger.error(err)
            return ToolResult(success=False, error=err)

    def list_tools(self) -> list[str]:
        """List all registered tools."""
        return list(self._tools.keys()) + list(self._functions.keys())


# Global registry instance
_global_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _global_registry
