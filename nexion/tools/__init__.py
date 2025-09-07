"""
Tool system for Nexion - Easy tool registration and management.

Usage:
    from nexion.tools import tool, register_tools

    @tool(name="weather", description="Get weather for a city")
    def get_weather(city: str) -> dict:
        return {"temp": 72, "conditions": "sunny"}

    # Auto-register all decorated functions in current module
    register_tools()
"""

import inspect
import sys

from .base import BaseTool, ToolResult, ToolSchema, tool
from .registry import get_tool_registry


def register_tools(module_name: str | None = None):
    """
    Register all @tool decorated functions from a module.

    Args:
        module_name: Module name to scan. If None, scans the calling module.
    """
    registry = get_tool_registry()

    # Get calling module if not specified
    if module_name is None:
        frame = inspect.currentframe().f_back
        module_name = frame.f_globals["__name__"]

    # Get the module
    module = sys.modules.get(module_name)
    if not module:
        raise ValueError(f"Module {module_name} not found")

    # Scan for decorated functions
    registered_count = 0
    for _name, obj in inspect.getmembers(module, inspect.isfunction):
        if hasattr(obj, "_tool_name"):
            registry.register_function(obj)
            registered_count += 1

    print(f"=' Registered {registered_count} tools from module {module_name}")


def list_registered_tools() -> list[str]:
    """List all currently registered tools."""
    registry = get_tool_registry()
    return registry.list_tools()


# Do not auto-register any built-in tools on import

# Export main interfaces
__all__ = [
    "tool",
    "BaseTool",
    "ToolSchema",
    "ToolResult",
    "register_tools",
    "list_registered_tools",
    "get_tool_registry",
]
