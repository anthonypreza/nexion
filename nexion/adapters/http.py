from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..config.bridge import get_config_bridge
from ..core.bot_manager import BotManager, get_bot_manager
from ..core.types import Channel, MessageEvent
from ..utils.logging import get_logger

router = APIRouter()
logger = get_logger("http")


class ChatIn(BaseModel):
    bot_id: str = "default"
    user_id: str
    message: str
    thread_id: str | None = None


def auth(
    authorization: str | None = Header(None),
):
    # Get HTTP key from workspace config
    bridge = get_config_bridge()
    workspace_config = bridge.get_yaml_config()

    bot_http_key = None
    if "http" in workspace_config.adapters:
        bot_http_key = workspace_config.adapters["http"].api_key

    if bot_http_key and authorization != f"Bearer {bot_http_key}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def create_chat_handler(path: str):
    """Create a chat handler function for a specific path."""

    async def chat_handler(
        payload: ChatIn, bot_manager: BotManager = Depends(get_bot_manager)
    ):
        logger.info(
            f"Processing chat request on {path} from user {payload.user_id}: {payload.message[:50]}{'...' if len(payload.message) > 50 else ''}"
        )

        # Get the bot for this path
        runtime = bot_manager.get_bot_for_http_path(path)
        if not runtime:
            raise HTTPException(
                status_code=404, detail=f"No bot configured for path {path}"
            )

        event = MessageEvent(
            channel=Channel.HTTP,
            user_id=payload.user_id,
            text=payload.message,
            bot_id=payload.bot_id,
            workspace_id=bot_manager.get_workspace_id(),
            thread_id=payload.thread_id,
        )
        res = await runtime.handle(event)

        logger.info(
            f"Sent reply to user {payload.user_id}: {res.text[:50]}{'...' if len(res.text) > 50 else ''}"
        )
        return {"reply": res.text}

    return chat_handler


async def register_dynamic_routes():
    """Register dynamic routes based on bot manager configuration."""
    bot_manager = await get_bot_manager()

    for path, bot_id in bot_manager.http_routes.items():
        logger.info(f"Registering HTTP route: {path}")
        handler = create_chat_handler(path)
        router.add_api_route(
            path, handler, methods=["POST"], dependencies=[Depends(auth)]
        )

        # Also create a UI route for each bot
        ui_path = path.replace("/api/", "/ui/")
        logger.info(f"Registering UI route: {ui_path}")
        ui_handler = create_bot_ui_handler(path, bot_id)
        router.add_api_route(ui_path, ui_handler, methods=["GET"])


def create_bot_ui_handler(path: str, bot_id: str):
    """Create a UI handler function for a specific bot."""

    async def bot_ui_handler(bot_manager: BotManager = Depends(get_bot_manager)):
        """Chat UI for a specific bot"""
        # Get all available bots for navigation
        all_routes = list(bot_manager.http_routes.items())

        return HTMLResponse(create_bot_ui_html(path, bot_id, all_routes))

    return bot_ui_handler


def create_bot_ui_html(current_path: str, current_bot_id: str, all_routes: list) -> str:
    """Generate HTML for a specific bot's UI."""
    # Create navigation links
    nav_links = []
    for route_path, route_bot_id in all_routes:
        ui_path = route_path.replace("/api/", "/ui/")
        active_class = "active" if route_path == current_path else ""
        nav_links.append(
            f'<a href="{ui_path}" class="nav-link {active_class}">{route_bot_id.title()} Bot</a>'
        )

    navigation_html = "\n".join(nav_links)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nexion Bot Chat</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px; margin: 0 auto; padding: 20px;
                background: #f5f5f5;
            }}
            .chat-container {{
                background: white; border-radius: 12px; padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .messages {{
                height: 400px; overflow-y: auto; border: 1px solid #ddd;
                padding: 15px; margin: 15px 0; border-radius: 8px;
                background: #fafafa;
            }}
            .message {{
                margin: 10px 0; padding: 8px 12px; border-radius: 8px;
                white-space: pre-wrap; word-wrap: break-word;
            }}
            .user {{ background: #007bff; color: white; margin-left: 20%; }}
            .bot {{ background: #e9ecef; color: #333; margin-right: 20%; }}
            .input-group {{ display: flex; gap: 10px; }}
            input {{
                flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 8px;
                font-size: 16px;
            }}
            button {{
                padding: 12px 20px; background: #007bff; color: white;
                border: none; border-radius: 8px; cursor: pointer; font-size: 16px;
            }}
            button:hover {{ background: #0056b3; }}
            button:disabled {{ background: #ccc; cursor: not-allowed; }}
            .error {{ background: #f8d7da; color: #721c24; padding: 10px; border-radius: 6px; margin: 10px 0; }}
            .settings {{ margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }}
            .settings input {{ flex: none; width: 200px; }}
            .nav-container {{ margin-bottom: 20px; padding: 15px; background: #e9ecef; border-radius: 8px; }}
            .nav-container strong {{ display: block; margin-bottom: 10px; }}
            .nav-links {{ display: flex; flex-wrap: wrap; gap: 10px; }}
            .nav-link {{ padding: 8px 16px; background: #fff; color: #007bff; text-decoration: none; border-radius: 6px; border: 1px solid #007bff; display: inline-block; }}
            .nav-link:hover {{ background: #007bff; color: white; }}
            .nav-link.active {{ background: #007bff; color: white; }}
            .bot-title {{ color: #007bff; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="chat-container">
            <h1 class="bot-title">🤖 {current_bot_id.title()} Bot Chat</h1>

            <div class="nav-container">
                <strong>Switch to other bots:</strong>
                <div class="nav-links">
                    {navigation_html}
                </div>
            </div>

            <div class="settings">
                <input type="text" id="userId" placeholder="User ID" value="user123">
                <input type="text" id="apiKey" placeholder="API Key" value="dev-secret">
                <div style="font-size: 12px; color: #666; margin-top: 5px;">
                    ⚠️ Default API key is "dev-secret" - change this in production!
                </div>
            </div>

            <div id="messages" class="messages"></div>
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="Type your message..." onkeypress="handleEnter(event)">
                <button onclick="sendMessage()" id="sendBtn">Send</button>
            </div>
        </div>

        <script>
            const messages = document.getElementById('messages');
            const messageInput = document.getElementById('messageInput');
            const sendBtn = document.getElementById('sendBtn');
            let userId = localStorage.getItem('nexion_user_id') || 'user_' + Date.now();
            localStorage.setItem('nexion_user_id', userId);
            document.getElementById('userId').value = userId;

            function addMessage(text, isUser = false) {{
                const div = document.createElement('div');
                div.className = `message ${{isUser ? 'user' : 'bot'}}`;
                div.textContent = text;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }}

            function handleEnter(event) {{
                if (event.key === 'Enter' && !event.shiftKey) {{
                    event.preventDefault();
                    sendMessage();
                }}
            }}

            async function sendMessage() {{
                const message = messageInput.value.trim();
                if (!message) return;

                const userId = document.getElementById('userId').value || 'anonymous';
                const apiKey = document.getElementById('apiKey').value;

                addMessage(message, true);
                messageInput.value = '';
                sendBtn.disabled = true;
                sendBtn.textContent = 'Sending...';

                try {{
                    const headers = {{
                        'Content-Type': 'application/json'
                    }};

                    if (apiKey) {{
                        headers['Authorization'] = `Bearer ${{apiKey}}`;
                    }}

                    const response = await fetch('{current_path}', {{
                        method: 'POST',
                        headers,
                        body: JSON.stringify({{
                            user_id: userId,
                            message: message,
                            bot_id: '{current_bot_id}'
                        }})
                    }});

                    if (!response.ok) {{
                        const error = await response.json();
                        throw new Error(error.detail || `HTTP ${{response.status}}`);
                    }}

                    const data = await response.json();
                    addMessage(data.reply);

                }} catch (error) {{
                    addMessage(`Error: ${{error.message}}`, false);
                    console.error('Chat error:', error);
                }}

                sendBtn.disabled = false;
                sendBtn.textContent = 'Send';
                messageInput.focus();
            }}

            // Focus on input when page loads
            messageInput.focus();

            // Add welcome message
            addMessage('Hi! I\\'m your {current_bot_id.title()} bot. Ask me anything!');
        </script>
    </body>
    </html>
    """
    return html


@router.get("/", response_class=HTMLResponse)
async def main_ui(bot_manager: BotManager = Depends(get_bot_manager)):
    """Main UI showing all available bots"""
    all_routes = list(bot_manager.http_routes.items())

    if len(all_routes) == 1:
        # If only one bot, redirect to its UI
        path, bot_id = all_routes[0]
        ui_path = path.replace("/api/", "/ui/")
        return HTMLResponse(f'<script>window.location.href="{ui_path}";</script>')

    # Multiple bots - show selection page
    bot_links = []
    for route_path, route_bot_id in all_routes:
        ui_path = route_path.replace("/api/", "/ui/")
        bot_links.append(
            f'<a href="{ui_path}" class="bot-card"><h3>{route_bot_id.title()} Bot</h3><p>Chat with the {route_bot_id} bot</p></a>'
        )

    bot_cards_html = "\n".join(bot_links)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nexion Bots</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px; margin: 0 auto; padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white; border-radius: 12px; padding: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;
            }}
            .bot-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 30px; }}
            .bot-card {{
                display: block; padding: 20px; background: #f8f9fa; border: 2px solid #e9ecef;
                border-radius: 8px; text-decoration: none; color: #333; transition: all 0.3s;
            }}
            .bot-card:hover {{ border-color: #007bff; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            .bot-card h3 {{ margin: 0 0 10px 0; color: #007bff; }}
            .bot-card p {{ margin: 0; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Nexion Bots</h1>
            <p>Select a bot to start chatting:</p>

            <div class="bot-grid">
                {bot_cards_html}
            </div>
        </div>
    </body>
    </html>
    """
    return html


# Log when the HTTP router is imported
logger.info("HTTP adapter module loaded - dynamic routes will be registered at startup")
