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

    # Peek at YAML for optional log_level before initializing logging
    level = None
    try:
        cfg = ConfigLoader().load()
        level = cfg.log_level
    except Exception:
        level = None

    setup_logging(level)
    logger = get_logger("server")

    # Startup
    logger.info("🚀 Starting Nexion server...")
    bot_manager = await get_bot_manager()
    # Summarize providers/models for all bots after initialization
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


def run(port: int = 8080):
    # Store port for the lifespan function
    import asyncio
    import os

    os.environ["NEXION_SERVER_PORT"] = str(port)

    # Create the app with dynamic routes
    app = asyncio.run(create_app())
    uvicorn.run(app, host="0.0.0.0", port=port)
