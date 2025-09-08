from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from ..adapters.http import register_dynamic_routes
from ..adapters.http import router as http_router
from ..adapters.telegram import start_telegram_polling, stop_telegram_polling
from ..config.yaml import ConfigLoader
from ..core.bot_manager import get_bot_manager
from ..utils.logging import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load .env as early as possible so log level env is available
    try:
        from dotenv import load_dotenv

        env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except Exception:
        pass

    # Get config path from environment (set by run function)
    import os

    config_path_str = os.environ.get("NEXION_CONFIG_PATH")
    config_path = Path(config_path_str) if config_path_str else None

    # Peek at YAML for optional log_level before initializing logging
    level = None
    try:
        cfg = ConfigLoader(config_path).load()
        level = cfg.log_level
    except Exception:
        level = None

    setup_logging(level)
    logger = get_logger("server")

    # Log which config file is being used
    if config_path:
        logger.info(f"📄 Using configuration file: {config_path}")
    else:
        logger.info("📄 Using default configuration file: bot.yml")

    # Startup
    logger.info("🚀 Starting Nexion server...")
    bot_manager = await get_bot_manager(config_path)
    # Summarize providers/models/tools for all bots after initialization
    try:
        for bot_id, agent in bot_manager.bots.items():
            provider_obj = getattr(agent, "provider", None)
            # Resolve channels from workspace config
            channels = []
            try:
                cfgs = [b for b in bot_manager.workspace_config.bots if b.id == bot_id]
                if cfgs:
                    channels = [
                        c if isinstance(c, str) else c.channel for c in cfgs[0].channels
                    ]
            except Exception:
                channels = []

            if provider_obj:
                provider_type = provider_obj.__class__.__name__.replace(
                    "Provider", ""
                ).lower()
                logger.info(
                    f"🧩 Bot '{bot_id}': provider={provider_type} model={agent.model}"
                )
            else:
                logger.info(f"🧩 Bot '{bot_id}': provider=none (echo mode)")
            logger.info(
                f"   ↳ channels: {', '.join(channels) if channels else '(none)'}"
            )

            # Log tools available to this bot
            bot_tools = agent.settings.tools
            available_tools = agent.tool_registry.list_tools()
            enabled_tools = [tool for tool in bot_tools if tool in available_tools]
            disabled_tools = [tool for tool in bot_tools if tool not in available_tools]

            if enabled_tools:
                logger.info(f"   ↳ tools: {', '.join(enabled_tools)}")
            if disabled_tools:
                logger.warning(
                    f"   ↳ disabled tools: {', '.join(disabled_tools)} (not found in registry)"
                )
            if not bot_tools:
                logger.info("   ↳ tools: (none configured)")

    except Exception as e:
        logger.warning(f"Could not log bot provider summary: {e}")

    # Start telegram polling
    await start_telegram_polling(bot_manager)

    # Get the port from environment variable set by run()
    import os

    port = os.environ.get("NEXION_SERVER_PORT", "8080")

    logger.info("✅ All services started successfully")
    logger.info(
        f"🌐 Visit http://localhost:{port}/ to interact with your bot via web UI"
    )

    yield

    # Shutdown
    logger.info("🛑 Shutting down Nexion server...")
    await stop_telegram_polling()
    logger.info("✅ Server shutdown complete")


async def create_app() -> FastAPI:
    await register_dynamic_routes()

    app = FastAPI(title="Nexion", lifespan=lifespan)
    app.include_router(http_router)

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    return app


def run(port: int = 8080, config_path: Path | None = None):
    # Store port and config path for the lifespan function
    import asyncio
    import os

    os.environ["NEXION_SERVER_PORT"] = str(port)
    if config_path:
        os.environ["NEXION_CONFIG_PATH"] = str(config_path)

    # Create the app with dynamic routes
    app = asyncio.run(create_app())
    uvicorn.run(app, host="0.0.0.0", port=port)
