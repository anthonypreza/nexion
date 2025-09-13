import asyncio
import json
from typing import ClassVar

import httpx
from httpx_ws import aconnect_ws

from ..core.bot_manager import BotManager
from ..core.types import Channel, MessageEvent
from ..utils.logging import get_logger

logger = get_logger("discord")


class DiscordWebsocketService:
    API_BASE_URL: ClassVar[str] = "https://discord.com/api"
    API_VERSION: ClassVar[int] = 10
    API_URL: ClassVar[str] = f"{API_BASE_URL}/v{API_VERSION}"

    def __init__(self, bot_token: str, bot_manager: BotManager, bot_username: str):
        self.bot_token = bot_token
        self.bot_manager = bot_manager
        self.bot_username = bot_username
        self.running = False
        self.task: asyncio.Task | None = None
        self.websocket_url: str | None = None
        self.heartbeat: asyncio.Task | None = None
        self.heartbeat_interval: int | None = None
        self.last_heartbeat: int | None = None
        self.heartbeat_active = False

        # Session tracking for resume functionality
        self.session_id: str | None = None
        self.sequence_number: int | None = None
        self.resume_gateway_url: str | None = None
        self.can_resume: bool = False

        # Reusable HTTP client for API requests
        self.http_client: httpx.AsyncClient | None = None

    async def start(self):
        """Starts the Discord websocket service."""
        if self.running:
            return

        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(timeout=30)

        self.running = True
        self.task = asyncio.create_task(self._websocket())
        logger.info(f"Discord websocket started for bot {self.bot_username}")

    async def stop(self):
        """Stops the Discord websocket service."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        # Clean up HTTP client
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

        logger.info(f"Discord websocket service stopped for bot {self.bot_username}")

    async def _websocket(self):
        """Main websocket service."""
        try:
            # Set initial websocket URL
            if not self.websocket_url:
                self.websocket_url = await self._get_websocket_url()

            while self.running:
                try:
                    # Determine which URL to use - resume URL if we can resume, otherwise regular URL
                    connection_url = self.websocket_url
                    if self.can_resume and self.resume_gateway_url:
                        connection_url = self.resume_gateway_url
                        logger.info(
                            f"Attempting to resume connection for bot {self.bot_username} using resume gateway URL"
                        )
                    else:
                        logger.info(
                            f"Starting fresh connection for bot {self.bot_username} using regular gateway URL"
                        )

                    # Connect to websocket
                    async with httpx.AsyncClient() as client:
                        async with aconnect_ws(connection_url, client) as ws:
                            # Receive Hello event
                            msg = await ws.receive_text()
                            msg_json = json.loads(msg)

                            if msg_json["op"] != 10:
                                logger.warning(
                                    "Discord websocket didn't return Hello event"
                                )
                                return

                            self.heartbeat_interval = msg_json["d"][
                                "heartbeat_interval"
                            ]
                            logger.info(
                                f"Received Hello event with heartbeat interval: {self.heartbeat_interval} ms"
                            )

                            # Send RESUME or IDENTIFY payload based on session state
                            if (
                                self.can_resume
                                and self.session_id
                                and self.sequence_number is not None
                            ):
                                logger.info(
                                    f"Attempting to resume session for bot {self.bot_username}"
                                )
                                success = await self._send_resume(ws)
                                if not success:
                                    logger.warning(
                                        f"Resume failed for bot {self.bot_username}, falling back to identify"
                                    )
                                    await self._send_identify(ws)
                            else:
                                logger.info(
                                    f"Starting fresh session for bot {self.bot_username}"
                                )
                                await self._send_identify(ws)

                            # Start heartbeat in background
                            self.heartbeat_active = True
                            self.heartbeat = asyncio.create_task(
                                self._heartbeat_loop(ws)
                            )
                            logger.debug("Started heartbeat task")

                            # Main message loop
                            logger.debug("Entering main message loop")
                            try:
                                while self.heartbeat_active and self.running:
                                    try:
                                        logger.debug("Waiting for message...")
                                        msg = await ws.receive_text()
                                        msg_json = json.loads(msg)
                                        logger.debug(f"Received message: {msg_json}")
                                        await self._handle_message(msg_json, ws)
                                    except asyncio.TimeoutError:
                                        # Timeout is expected, just continue the loop
                                        logger.debug("Message timeout, continuing...")
                                        continue
                                    except Exception as e:
                                        logger.error(
                                            f"Error processing Discord message: {e}"
                                        )
                                        break
                            finally:
                                self.heartbeat_active = False
                                if self.heartbeat and not self.heartbeat.done():
                                    self.heartbeat.cancel()
                                    try:
                                        await self.heartbeat
                                    except asyncio.CancelledError:
                                        pass

                except (httpx.ReadError, httpx.ConnectError, ConnectionError) as e:
                    logger.error(
                        f"WebSocket connection error for Discord bot {self.bot_username}: {e}"
                    )
                    if self.running:
                        await asyncio.sleep(5)  # Wait before reconnecting

        except Exception as e:
            logger.error(
                f"Fatal error in Discord websocket for bot {self.bot_username}: {e}"
            )
        finally:
            self.heartbeat_active = False

    async def _heartbeat_loop(self, ws):
        """Background heartbeat process as required by Discord."""
        logger.info(
            f"Starting heartbeat for Discord bot {self.bot_username} with interval {self.heartbeat_interval} ms"
        )

        try:
            while self.heartbeat_active:
                try:
                    logger.debug(
                        f"Sending heartbeat for Discord bot {self.bot_username}"
                    )
                    await ws.send_text(json.dumps({"op": 1, "d": self.last_heartbeat}))
                    await asyncio.sleep(self.heartbeat_interval / 1000)
                except Exception as e:
                    logger.error(
                        f"Failed to send heartbeat for Discord bot {self.bot_username}: {e}"
                    )
                    self.heartbeat_active = False
                    break

        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled for Discord bot {self.bot_username}")
        finally:
            self.heartbeat_active = False

    async def _handle_message(self, msg_json, ws):
        """Handle incoming Discord messages."""
        op = msg_json.get("op")

        if op == 11:  # Heartbeat ACK
            logger.debug(f"Received heartbeat ACK for Discord bot {self.bot_username}")
            self.last_heartbeat = msg_json.get("s")

        elif op == 1:  # Heartbeat request from Discord
            logger.debug(
                f"Received heartbeat request for Discord bot {self.bot_username}"
            )
            # Send immediate heartbeat response
            try:
                await ws.send_text(json.dumps({"op": 1, "d": self.last_heartbeat}))
            except Exception as e:
                logger.error(
                    f"Failed to send heartbeat response for Discord bot {self.bot_username}: {e}"
                )
                self.heartbeat_active = False

        elif op == 0:  # Dispatch (events)
            # Update sequence number for resume functionality (for opcode 0 events)
            if msg_json.get("s") is not None:
                self.sequence_number = msg_json.get("s")

            event_type = msg_json.get("t")
            logger.debug(
                f"Received Discord event {event_type} for bot {self.bot_username}"
            )

            if event_type == "READY":
                logger.info(
                    f"Bot {self.bot_username} successfully connected and ready!"
                )

                # Extract session information for resume functionality
                ready_data = msg_json.get("d", {})
                self.session_id = ready_data.get("session_id")
                self.resume_gateway_url = ready_data.get("resume_gateway_url")
                self.can_resume = True

                logger.info(
                    f"Session established for bot {self.bot_username}, session_id: {self.session_id}"
                )
                logger.debug(f"Resume gateway URL: {self.resume_gateway_url}")

            elif event_type == "RESUMED":
                logger.info(f"Bot {self.bot_username} successfully resumed session!")
                # Session information should already be intact from before the disconnect

            elif event_type == "MESSAGE_CREATE":
                logger.info(
                    f"Received MESSAGE_CREATE event for bot {self.bot_username}"
                )

                msg_data = msg_json.get("d")

                # Ignore messages from bots (including this bot)
                if msg_data.get("author", {}).get("bot", False):
                    logger.debug("Ignoring message from bot user")
                    return

                content = msg_data.get("content", "")
                if not content:
                    return

                user_id = msg_data.get("author", {}).get("id")
                user_name = msg_data.get("author", {}).get("username")
                chat_id = msg_data.get("channel_id")

                if not chat_id:
                    return

                # Get the appropriate bot runtime for this Discord username
                runtime = self.bot_manager.get_bot_for_discord(self.bot_username)
                if not runtime:
                    logger.error(
                        f"No bot configured for Discord username {self.bot_username}"
                    )
                    return

                event = MessageEvent(
                    channel=Channel.DISCORD,
                    user_id=str(user_id),
                    text=content,
                    bot_id=self.bot_manager.discord_bots.get(
                        self.bot_username, "default"
                    ),
                    workspace_id=self.bot_manager.get_workspace_id(),
                    chat_id=str(chat_id),
                    metadata={
                        "discord_user_id": user_id,
                        "discord_user_name": user_name,
                        "discord_chat_id": chat_id,
                    },
                )

                logger.info(
                    f"Processing Discord message from user {user_id}: {content[:50]}{'...' if len(content) > 50 else ''}"
                )

                try:
                    reply = await runtime.handle(event)
                    await self._send_message(int(event.chat_id), reply.text)
                    logger.info(
                        f"Sent Discord reply to user {user_id}: {reply.text[:50]}{'...' if len(reply.text) > 50 else ''}"
                    )
                except Exception as e:
                    logger.error(f"Error processing Discord message: {e}")

        elif op == 9:  # Invalid Session
            resumable = msg_json.get("d", False)
            logger.warning(
                f"Invalid session for bot {self.bot_username}, resumable: {resumable}"
            )

            # Clear resume state if the session is not resumable
            if not resumable:
                logger.info(
                    f"Session not resumable for bot {self.bot_username}, clearing session state"
                )
                self.session_id = None
                self.sequence_number = None
                self.can_resume = False

            self.heartbeat_active = False  # Stop heartbeat and reconnect

        else:
            logger.debug(
                f"Received Discord message with op {op} for bot {self.bot_username}"
            )

    async def _send_message(self, chat_id: int, text: str):
        if not self.http_client:
            logger.error("HTTP client not initialized")
            return

        url = f"{DiscordWebsocketService.API_URL}/channels/{chat_id}/messages"
        await self.http_client.post(
            url, json={"content": text, "tts": False}, headers=self._get_headers()
        )

    async def _get_websocket_url(self):
        if not self.http_client:
            logger.error("HTTP client not initialized")
            return None

        url = f"{DiscordWebsocketService.API_URL}/gateway/bot"

        response = await self.http_client.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()

        if not data.get("url"):
            logger.warning("Discord websocket service did not return a url")
            return None

        return data["url"]

    def _get_headers(self):
        return {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }

    async def _send_resume(self, ws):
        """Send Resume (opcode 6) payload to Discord."""
        if not self.session_id or self.sequence_number is None:
            logger.warning(
                f"Cannot resume - missing session_id or sequence_number for bot {self.bot_username}"
            )
            return False

        resume_payload = {
            "op": 6,
            "d": {
                "token": self.bot_token,
                "session_id": self.session_id,
                "seq": self.sequence_number,
            },
        }

        try:
            await ws.send_text(json.dumps(resume_payload))
            logger.info(
                f"Sent RESUME payload for bot {self.bot_username} (session: {self.session_id}, seq: {self.sequence_number})"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to send RESUME payload for bot {self.bot_username}: {e}"
            )
            return False

    async def _send_identify(self, ws):
        """Send Identify (opcode 2) payload to Discord."""
        identify_payload = {
            "op": 2,
            "d": {
                "token": self.bot_token,
                "intents": 4096,  # DIRECT_MESSAGES (1 << 12)
                "properties": {"os": "linux", "browser": "nexion", "device": "nexion"},
            },
        }

        try:
            await ws.send_text(json.dumps(identify_payload))
            logger.info("Sent IDENTIFY payload for DIRECT_MESSAGES")
            return True
        except Exception as e:
            logger.error(
                f"Failed to send IDENTIFY payload for bot {self.bot_username}: {e}"
            )
            return False


# Global websocket service instances
_websocket_services: list[DiscordWebsocketService] = []


async def start_discord_websockets(bot_manager: BotManager):
    """Start Discord websocket services for all configured Discord bots"""
    global _websocket_services

    # Collect all Discord bot configurations with their tokens
    discord_bot_configs = []  # List of (bot_token, bot_username) tuples

    for bot_id, runtime in bot_manager.bots.items():
        logger.debug(f"Checking bot {bot_id}: {runtime}")
        # Check each channel in this bot's settings
        for channel_path, channel_config in runtime.settings.channel_configs.items():
            logger.debug(f"Checking channel config: {channel_path} -> {channel_config}")
            if channel_path.startswith("discord:"):
                bot_username = channel_path[8:]  # Remove "discord:" prefix
                bot_token = channel_config.get("bot_token")

                if bot_token:
                    discord_bot_configs.append((bot_token, bot_username))
                    logger.info(f"Found Discord bot config: {bot_username} -> {bot_id}")

    # Remove duplicate token/username combinations
    unique_discord_configs = list(set(discord_bot_configs))

    # Start a websocket service for each unique Discord bot token/username
    for bot_token, bot_username in unique_discord_configs:
        logger.info(f"Starting Discord websocket service for {bot_username}")
        service = DiscordWebsocketService(bot_token, bot_manager, bot_username)
        _websocket_services.append(service)
        await service.start()

    if unique_discord_configs:
        logger.info(f"Started {len(unique_discord_configs)} Discord websocket services")
    else:
        logger.info("No Discord bots configured")


async def stop_discord_websockets():
    """Stop all Discord websocket services"""
    global _websocket_services

    for service in _websocket_services:
        await service.stop()

    _websocket_services.clear()
    logger.info("All Discord websocket services stopped")
