import asyncio

import httpx
from fastapi import APIRouter

from ..config.settings import Settings
from ..core.agent import AgentRuntime
from ..core.types import Channel, MessageEvent
from ..utils.logging import get_logger

router = APIRouter()
logger = get_logger("telegram")


class TelegramPollingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.last_update_id = 0
        self.running = False
        self.task: asyncio.Task | None = None

    async def start(self):
        """Start the polling service"""
        if not self.settings.TELEGRAM_BOT_TOKEN:
            logger.info("Telegram bot token not configured, skipping Telegram polling")
            return

        if self.running:
            return

        self.running = True
        self.task = asyncio.create_task(self._poll_loop())
        logger.info("Telegram polling service started")

    async def stop(self):
        """Stop the polling service"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Telegram polling service stopped")

    async def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                await self._get_updates()
                await asyncio.sleep(1)  # Poll every second
            except Exception as e:
                logger.error(f"Error in Telegram polling: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def _get_updates(self):
        """Fetch updates from Telegram"""
        async with httpx.AsyncClient(timeout=30) as client:
            url = f"https://api.telegram.org/bot{self.settings.TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {
                "offset": self.last_update_id + 1,
                "timeout": 10,  # Long polling timeout
                "allowed_updates": ["message"],
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                logger.error(f"Telegram API error: {data}")
                return

            updates = data.get("result", [])
            for update in updates:
                await self._process_update(update)
                self.last_update_id = max(self.last_update_id, update["update_id"])

    async def _process_update(self, update: dict):
        """Process a single update from Telegram"""
        if "message" not in update:
            return

        msg = update["message"]
        text = msg.get("text", "")
        if not text:
            return

        user_id = str(msg.get("from", {}).get("id", "unknown"))
        chat_id = msg.get("chat", {}).get("id")

        if not chat_id:
            return

        # Process the message
        runtime = AgentRuntime(self.settings)
        await runtime.initialize()

        event = MessageEvent(
            channel=Channel.TELEGRAM,
            user_id=str(chat_id),
            text=text,
            bot_id="default",  # TODO: Make these configurable
            workspace_id="default",
            metadata={"telegram_user_id": user_id, "telegram_chat_id": chat_id},
        )

        logger.info(
            f"Processing Telegram message from user {user_id}: {text[:50]}{'...' if len(text) > 50 else ''}"
        )

        try:
            reply = await runtime.handle(event)
            await self._send_message(chat_id, reply.text)
            logger.info(
                f"Sent Telegram reply to user {user_id}: {reply.text[:50]}{'...' if len(reply.text) > 50 else ''}"
            )
        except Exception as e:
            logger.error(f"Error processing Telegram message: {e}")

    async def _send_message(self, chat_id: int, text: str):
        """Send a message to Telegram"""
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"https://api.telegram.org/bot{self.settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            await client.post(url, json={"chat_id": chat_id, "text": text})


# Global polling service instance
_polling_service: TelegramPollingService | None = None


async def start_telegram_polling(settings: Settings):
    """Start the Telegram polling service"""
    global _polling_service
    if _polling_service is None:
        _polling_service = TelegramPollingService(settings)
    await _polling_service.start()


async def stop_telegram_polling():
    """Stop the Telegram polling service"""
    global _polling_service
    if _polling_service:
        await _polling_service.stop()
