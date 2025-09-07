from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from ..adapters.http import register_dynamic_routes
from ..adapters.http import router as http_router
from ..adapters.telegram import start_telegram_polling, stop_telegram_polling
from ..core.bot_manager import get_bot_manager
from ..utils.logging import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger("server")

    # Startup
    logger.info("🚀 Starting Nexion server...")
    bot_manager = await get_bot_manager()

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
