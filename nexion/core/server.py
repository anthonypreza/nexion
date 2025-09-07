import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from ..adapters.http import router as http_router, register_dynamic_routes
from ..adapters.telegram import start_telegram_polling, stop_telegram_polling
from ..config.bridge import get_settings_from_yaml
from ..utils.logging import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger("server")

    # Startup
    logger.info("🚀 Starting Nexion server...")
    settings = get_settings_from_yaml()
    logger.info(f"📝 Configuration loaded (model: {settings.MODEL})")

    # Start telegram polling
    await start_telegram_polling(settings)

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
    import os
    import asyncio

    os.environ["NEXION_SERVER_PORT"] = str(port)

    # Create the app with dynamic routes
    app = asyncio.run(create_app())
    uvicorn.run(app, host="0.0.0.0", port=port)
