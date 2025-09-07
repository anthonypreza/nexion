"""
Example custom tools for Nexion bots.

Define functions with the @tool decorator – they will be auto-discovered.
Includes a simple fetch_joke tool that calls a public API.
"""

from typing import Any

import httpx

from nexion.tools import tool


@tool(name="weather", description="Get weather information for a city")
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get weather for a city.

    city: The city name to get weather for
    units: Temperature units (Celsius or Fahrenheit)
    """
    # This is a mock implementation - replace with real weather API
    return {
        "city": city,
        "temperature": 22 if units == "celsius" else 72,
        "conditions": "sunny",
        "units": units,
    }


@tool(name="calculate", description="Perform basic mathematical calculations")
def calculate(expression: str) -> dict:
    """Calculate a mathematical expression.

    expression: A mathematical expression like "2 + 2" or "10 * 5"
    """
    try:
        # Simple eval - in production you'd want a safer math parser
        result = eval(expression)
        return {"expression": expression, "result": result, "success": True}
    except Exception as e:
        return {"expression": expression, "error": str(e), "success": False}


@tool(name="fetch_joke", description="Fetch a random joke from a public API")
def fetch_joke(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch JSON from a jokes API.

    params: Optional query parameters to include
    """
    url = "https://official-joke-api.appspot.com/random_joke"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params or {})
            resp.raise_for_status()
            data = (
                resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else resp.text
            )
            return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Tools are auto-discovered when the bot starts - no manual registration needed!
if __name__ == "__main__":
    print("This file defines custom tools that will be auto-discovered by Nexion.")
    print("Simply run: nexctl dev")
    print()
    print("Defined tools:")
    print("- weather: Get weather for any city")
    print("- calculate: Perform mathematical calculations")
    print("- fetch_joke: Fetch a random joke from a public API")
