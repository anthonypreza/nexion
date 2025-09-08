from pathlib import Path

import typer

from nexion.core.server import run

app = typer.Typer(
    help="Nexion AI Agent Framework - Build and deploy multi-channel bots",
    epilog="Visit https://github.com/anthonypreza/nexion for documentation and examples",
)


@app.command()
def dev(
    port: int = typer.Option(8080, help="Port to run the development server on"),
    config: str = typer.Option(
        "bot.yml", "--config", "-c", help="Path to the bot configuration file"
    ),
):
    """Start the Nexion development server with web UI and API endpoints."""
    config_path = Path(config)
    if not config_path.exists():
        typer.echo(f"❌ Configuration file not found: {config_path}", err=True)
        raise typer.Exit(1)

    run(port=port, config_path=config_path)


@app.command()
def init(
    project_name: str = typer.Argument(
        ".", help="Project directory name or '.' for current directory"
    ),
):
    """Create a new Nexion bot project with configuration templates."""
    _init_project(project_name)


def _init_project(project_name: str):
    """Initialize a new Nexion bot project."""
    if project_name == ".":
        project_path = Path.cwd()
        typer.echo(f"Initializing Nexion project in current directory: {project_path}")
    else:
        project_path = Path.cwd() / project_name
        project_path.mkdir(exist_ok=True)
        typer.echo(f"Creating new Nexion project: {project_path}")

    # Create bot.yml
    bot_yml_content = f"""workspace: {project_path.name}
profiles: [default]

bots:
  - id: my-assistant
    channels:
      - "http:/api/chat"
    system_prompt: prompts/system.md
    model: openai:gpt-4o-mini

providers:
  openai:
    api_key: env:OPENAI_API_KEY

adapters:
  http:
    api_key: env:BOT_HTTP_KEY
"""

    # Create system prompt
    system_prompt_content = """You are a friendly and helpful assistant.

Guidelines:
- Always be helpful, professional, and concise
- When you don't know something, say so and offer alternatives
- Focus on solving the user's problem quickly
- Use a warm, conversational tone
"""

    # Create .env.example
    env_example_content = """OPENAI_API_KEY=
BOT_HTTP_KEY=dev-secret
"""

    # Write files
    (project_path / "bot.yml").write_text(bot_yml_content)
    typer.echo("  ✓ Created bot.yml")

    prompts_dir = project_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    (prompts_dir / "system.md").write_text(system_prompt_content)
    typer.echo("  ✓ Created prompts/system.md")

    (project_path / ".env.example").write_text(env_example_content)
    typer.echo("  ✓ Created .env.example")

    typer.echo()
    typer.echo("🎉 Project initialized successfully!")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("1. Copy .env.example to .env and add your API keys")
    typer.echo("2. Run 'nexctl dev' to start your bot")
    typer.echo("3. Visit http://localhost:8080 to chat with your bot")


# Show help when no command is specified
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Nexion AI Agent Framework - Build and deploy multi-channel bots.

    Use 'nexctl dev' to start the development server or 'nexctl init' to create a new project.
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided, show help
        print(ctx.get_help())
        raise typer.Exit()


if __name__ == "__main__":
    app()
