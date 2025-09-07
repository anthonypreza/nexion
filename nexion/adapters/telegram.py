import asyncio

import httpx
from fastapi import APIRouter

from ..core.bot_manager import BotManager
from ..core.types import Channel, MessageEvent
from ..utils.logging import get_logger

router = APIRouter()
logger = get_logger("telegram")


class TelegramPollingService:
    def __init__(self, bot_token: str, bot_manager: BotManager, bot_username: str):
        self.bot_token = bot_token
        self.bot_manager = bot_manager
        self.bot_username = bot_username  # e.g., "@supportbot"
        self.last_update_id = 0
        self.running = False
        self.task: asyncio.Task | None = None

    async def start(self):
        """Start the polling service"""
        if self.running:
            return

        self.running = True
        self.task = asyncio.create_task(self._poll_loop())
        logger.info(f"Telegram polling service started for bot {self.bot_username}")

    async def stop(self):
        """Stop the polling service"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info(f"Telegram polling service stopped for bot {self.bot_username}")

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
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
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

        # Get the appropriate bot runtime for this Telegram username
        runtime = self.bot_manager.get_bot_for_telegram(self.bot_username)
        if not runtime:
            logger.error(f"No bot configured for Telegram username {self.bot_username}")
            return

        event = MessageEvent(
            channel=Channel.TELEGRAM,
            user_id=str(chat_id),
            text=text,
            bot_id=self.bot_manager.telegram_bots.get(self.bot_username, "default"),
            workspace_id=self.bot_manager.get_workspace_id(),
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
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            await client.post(url, json={"chat_id": chat_id, "text": text})


# Global polling service instances
_polling_services: list[TelegramPollingService] = []


async def start_telegram_polling(bot_manager: BotManager):
    """Start Telegram polling services for all configured Telegram bots"""
    global _polling_services

    # Collect all Telegram bot configurations with their tokens
    telegram_bot_configs = []  # List of (bot_token, bot_username) tuples

    for bot_id, runtime in bot_manager.bots.items():
        # Check each channel in this bot's settings
        for channel_path, channel_config in runtime.settings.channel_configs.items():
            if channel_path.startswith("telegram:"):
                bot_username = channel_path[9:]  # Remove "telegram:" prefix
                bot_token = channel_config.get("bot_token")

                if bot_token:
                    telegram_bot_configs.append((bot_token, bot_username))
                    logger.info(
                        f"Found Telegram bot config: {bot_username} -> {bot_id}"
                    )

    # Remove duplicate token/username combinations
    unique_telegram_configs = list(set(telegram_bot_configs))

    # Start a polling service for each unique Telegram bot token/username
    for bot_token, bot_username in unique_telegram_configs:
        logger.info(f"Starting Telegram polling service for {bot_username}")
        service = TelegramPollingService(bot_token, bot_manager, bot_username)
        _polling_services.append(service)
        await service.start()

    if unique_telegram_configs:
        logger.info(f"Started {len(unique_telegram_configs)} Telegram polling services")
    else:
        logger.info("No Telegram bots configured")


async def stop_telegram_polling():
    """Stop all Telegram polling services"""
    global _polling_services

    for service in _polling_services:
        await service.stop()

    _polling_services.clear()
    logger.info("All Telegram polling services stopped")
