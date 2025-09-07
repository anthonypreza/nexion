import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


class ToolSchema(BaseModel):
    """JSON schema for tool function calling."""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolResult(BaseModel):
    """Tool execution result."""

    success: bool
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = {}


class BaseTool(ABC):
    """Base tool class."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError("Must be implemented by subclass")

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        raise NotImplementedError("Must be implemented by subclass")


def tool(name: str = None, description: str = None) -> Callable:
    """Decorator to register a tool function."""

    def wrapper(func: Callable) -> Callable:
        # Auto-generate schema from function signature
        func._tool_name = name or func.__name__
        func._tool_description = (
            description or func.__doc__ or f"Execute {func.__name__}"
        )
        func._tool_schema = _generate_schema_from_function(func)
        return func

    return wrapper


def _generate_schema_from_function(func: Callable) -> ToolSchema:
    """Generate JSON Schema from Python function signature and type hints"""

    signature = inspect.signature(func)
    parameters = {"type": "object", "properties": {}, "required": []}

    for param_name, param in signature.parameters.items():
        param_schema = {}

        # Get type annotation
        if param.annotation != inspect.Parameter.empty:
            param_schema.update(_python_type_to_json_schema(param.annotation))
        else:
            # Default to string if no type hint
            param_schema["type"] = "string"

        # Handle default values
        if param.default != inspect.Parameter.empty:
            param_schema["default"] = param.default
        else:
            # Required parameter
            parameters["required"].append(param_name)

        # Extract description from docstring if available
        docstring_desc = _extract_param_description(func, param_name)
        if docstring_desc:
            param_schema["description"] = docstring_desc

        parameters["properties"][param_name] = param_schema

    return ToolSchema(
        name=func._tool_name, description=func._tool_description, parameters=parameters
    )


def _python_type_to_json_schema(python_type) -> dict:
    """Convert Python type hints to JSON Schema type definitions"""
    from typing import Union, get_args, get_origin

    # Handle basic types
    if python_type is str:
        return {"type": "string"}
    elif python_type is int:
        return {"type": "integer"}
    elif python_type is float:
        return {"type": "number"}
    elif python_type is bool:
        return {"type": "boolean"}
    elif python_type is list:
        return {"type": "array"}
    elif python_type is dict:
        return {"type": "object"}

    # Handle generic types (List[str], Dict[str, int], etc.)
    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is list:
        schema = {"type": "array"}
        if args:
            schema["items"] = _python_type_to_json_schema(args[0])
        return schema

    elif origin is dict:
        schema = {"type": "object"}
        if len(args) >= 2:
            # Dict[str, ValueType] -> additionalProperties: ValueType schema
            schema["additionalProperties"] = _python_type_to_json_schema(args[1])
        return schema

    elif origin is Union:
        # Handle Optional[T] (Union[T, None]) and other unions
        non_none_args = [arg for arg in args if arg is not type(None)]

        if len(non_none_args) == 1:
            # Optional[T] case
            return _python_type_to_json_schema(non_none_args[0])
        else:
            # Multiple types union - use anyOf
            return {
                "anyOf": [_python_type_to_json_schema(arg) for arg in non_none_args]
            }

    # Handle string literals and Enums
    if hasattr(python_type, "__origin__") and python_type.__origin__ is Union:
        # Literal types like Literal["GET", "POST"]
        return {"enum": list(args)}

    # Default fallback
    return {"type": "string", "description": f"Type: {python_type}"}


def _extract_param_description(func: Callable, param_name: str) -> str | None:
    """Extract parameter description from docstring (Google/Sphinx style)"""
    if not func.__doc__:
        return None

    # Simple extraction - look for "param_name: description" patterns
    docstring = func.__doc__
    lines = docstring.split("\n")

    for line in lines:
        line = line.strip()
        if line.startswith(f"{param_name}:") or line.startswith(f"{param_name} :"):
            # Extract description after the colon
            return line.split(":", 1)[1].strip()

    return None
