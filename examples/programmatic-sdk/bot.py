"""
Programmatic Bot Creation Example

This example demonstrates how to create a Nexion bot entirely in Python code
without needing YAML configuration files. This approach gives you the most
control and flexibility for dynamic bot creation.
"""

from nexion import Bot, HttpConfig
from nexion.tools import tool


# Define custom tools using the @tool decorator
@tool("greet", "Greet a user with a personalized message")
def greet_user(name: str, style: str = "friendly") -> str:
    """Greet a user with different styles.

    Args:
        name: The name of the person to greet
        style: The greeting style (friendly, formal, casual)
    """
    styles = {
        "friendly": f"Hello {name}! 👋 It's wonderful to meet you!",
        "formal": f"Good day, {name}. I am pleased to make your acquaintance.",
        "casual": f"Hey {name}! What's up?",
    }
    return styles.get(style, styles["friendly"])


@tool("calculate", "Perform basic arithmetic operations")
def calculate(operation: str, a: float, b: float) -> str:
    """Perform basic arithmetic operations safely.

    Args:
        operation: The operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number
    """
    operations = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else "Error: Division by zero",
    }

    if operation.lower() in operations:
        result = operations[operation.lower()]
        return f"{a} {operation} {b} = {result}"
    else:
        return f"Unknown operation: {operation}. Supported: add, subtract, multiply, divide"


@tool("word_count", "Count words in a text")
def word_count(text: str) -> str:
    """Count the number of words in the provided text.

    Args:
        text: The text to analyze
    """
    words = len(text.split())
    chars = len(text)
    return f"Text analysis: {words} words, {chars} characters"


@tool("reverse_text", "Reverse the order of text")
def reverse_text(text: str) -> str:
    """Reverse the provided text.

    Args:
        text: The text to reverse
    """
    return text[::-1]


# Create the bot with programmatic configuration
bot = Bot(
    # Bot identity and model configuration
    bot_id="programmatic-demo-bot",
    model="openai:gpt-4o-mini",
    # LLM provider configuration with environment variables
    openai_api_key="env:OPENAI_API_KEY",
    # HTTP adapter configuration - simple REST API interface
    adapters=[
        HttpConfig(
            api_key="env:BOT_HTTP_KEY",  # Optional API key for authentication
            endpoint="/api/chat",
        )
    ],
    # Tools - mix of function objects and string references
    tools=[
        greet_user,  # Decorated function object
        calculate,  # Decorated function object
        word_count,  # Decorated function object
        reverse_text,  # Decorated function object
        "mcp__filesystem__read_file",  # String reference to MCP tool (if available)
    ],
    # System prompt configuration - can use inline or file path
    system_prompt="""You are Nexion, a helpful and friendly assistant bot.

You have access to several tools that you can use to help users:
- greet: Create personalized greetings in different styles
- calculate: Perform basic arithmetic operations
- word_count: Count words and characters in text
- reverse_text: Reverse the order of text
- mcp__filesystem__read_file: Read files from the filesystem (if MCP is configured)

When using tools, always explain what you're doing and provide clear, helpful responses.
Be conversational and engaging while remaining professional and accurate.""",
    # system_prompt_path="prompts/system.md",  # Alternative: load from file
    # Optional: Inline MCP server configuration
    mcp_config={
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "env": {},
        }
    },
)


def main():
    """Main entry point for the bot."""
    print("🤖 Starting Nexion programmatic bot...")
    print(f"🆔 Bot ID: {bot.settings.bot_id}")
    print(f"🧠 Model: {bot.settings.model}")
    print(f"🔧 Tools: {', '.join(bot.settings.tools)}")
    print("🌐 HTTP endpoint: /api/chat")
    print("\n📋 Available tools:")
    for tool_name in bot.settings.tools:
        print(f"   • {tool_name}")

    print("\n🚀 Starting bot server...")
    print("💡 Try making a POST request to http://localhost:8080/api/chat")
    print('   Example: {"message": "Hello! Can you greet Alice in a formal style?"}')

    # Start the bot
    bot.run()


if __name__ == "__main__":
    main()
