# Nexion Tools Example

This example demonstrates how to create and use custom tools with Nexion bots.

## Quick Start

1. **Define custom tools** in `tools.py`:
```python
from nexion.tools import tool

@tool(name="weather", description="Get weather for a city")
def get_weather(city: str, units: str = "celsius") -> dict:
    return {"city": city, "temp": 22, "conditions": "sunny"}
```

2. **Enable tools** in your `bot.yml`:
```yaml
bots:
  - id: my-bot
    tools:
      - weather       # Your custom tool
      - add           # Safe add tool (two integers)
      - fetch_joke    # Example API fetch tool
```

3. **Start the bot**:
```bash
nexctl dev
```

That's it! Your tools are automatically discovered and available to the LLM.

## How It Works

- **Auto-Discovery**: Nexion automatically scans your project for files matching patterns like:
  - `tools.py`
  - `tools/*.py`
  - `src/tools.py`
  - `src/tools/*.py`

- **Tool Registration**: Functions decorated with `@tool` are automatically registered when the bot starts

- **LLM Integration**: Tools are converted to JSON schemas and sent to the LLM for function calling

- **Type Safety**: Python type hints are automatically converted to JSON Schema parameters

## File Structure

```
your-bot-project/
├── bot.yml           # Bot configuration
├── tools.py          # Your custom tools (auto-discovered)
└── prompts/
    └── system.md     # System prompt explaining tool usage
```

## Built-in Tools

For safety, Nexion does not include a generic HTTP tool. Giving an unconstrained LLM free-form HTTP access can be risky. Instead, define narrowly scoped tools with allowlisted endpoints and controlled parameters. See the example below.

## Writing Custom Tools

### Basic Tool
```python
@tool(name="hello", description="Say hello to someone")
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

### Tool with Optional Parameters
```python
@tool(name="weather", description="Get weather information")
def get_weather(city: str, units: str = "celsius") -> dict:
    # units has a default value, so it's optional
    return {"city": city, "temp": 22, "units": units}
```

### Tool with Documentation
```python
@tool(name="add", description="Add two integers and return the sum")
def add(a: int, b: int) -> dict:
    """Add two integers.

    a: First integer
    b: Second integer
    """
    return {"a": a, "b": b, "sum": a + b}
```

### Example: Simple API Fetch Tool (jokes)
```python
from typing import Dict, Any, Optional
import httpx
from nexion.tools import tool

@tool(name="fetch_joke", description="Fetch joke from a pre-approved API endpoint")
def fetch_joke(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fetch JSON from a jokes API.

    params: Optional query parameters to include
    """
    url = "https://official-joke-api.appspot.com/random_joke"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params or {})
            resp.raise_for_status()
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Testing

Run the example:
```bash
cd examples/tools-example
nexctl dev           # Starts the bot with auto-discovered tools
```

Chat with your bot and try:
- "What's the weather in Tokyo?"
- "Add 15 and 24"
- "Fetch a joke"
