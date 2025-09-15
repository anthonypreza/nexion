import json

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..config.bridge import get_config_bridge
from ..core.bot_manager import get_bot_manager
from ..core.types import Channel, MessageEvent
from ..utils.logging import get_logger

router = APIRouter()
logger = get_logger("http")


class ChatIn(BaseModel):
    bot_id: str = "default"
    user_id: str
    message: str
    thread_id: str | None = None


class NewChatIn(BaseModel):
    bot_id: str = "default"
    user_id: str


def auth(
    authorization: str | None = Header(None),
):
    """Legacy global auth function - kept for backward compatibility."""
    # Get HTTP key from workspace config
    bridge = get_config_bridge()
    workspace_config = bridge.get_yaml_config()

    bot_http_key = None
    if "http" in workspace_config.adapters:
        bot_http_key = workspace_config.adapters["http"].api_key

    if bot_http_key and authorization != f"Bearer {bot_http_key}":
        raise HTTPException(status_code=401, detail="Unauthorized")


async def create_route_auth(path: str):
    """Create an async route-specific auth function that checks the API key for this specific path."""

    async def route_auth(authorization: str | None = Header(None)):
        bot_manager = await get_bot_manager()

        # Get the bot runtime for this path
        runtime = bot_manager.get_bot_for_http_path(path)
        if not runtime:
            raise HTTPException(
                status_code=404, detail=f"No bot configured for path {path}"
            )

        # Get the API key for this specific path from the bot's channel configs
        expected_key = runtime.settings.channel_configs.get(path, {}).get("api_key")

        if expected_key and authorization != f"Bearer {expected_key}":
            raise HTTPException(status_code=401, detail="Unauthorized")
        elif not expected_key:
            # No API key configured for this route - allow access (backward compatibility)
            pass

    return route_auth


def create_chat_handler(path: str):
    """Create a chat handler function for a specific path."""

    async def chat_handler(payload: ChatIn):
        logger.info(
            f"Processing chat request on {path} from user {payload.user_id}: {payload.message[:50]}{'...' if len(payload.message) > 50 else ''}"
        )

        # Get the bot manager and then the bot for this path
        bot_manager = await get_bot_manager()
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
            chat_id=payload.user_id,  # For HTTP, chat_id is the same as user_id
        )
        res = await runtime.handle(event)

        logger.info(
            f"Sent reply to user {payload.user_id}: {res.text[:50]}{'...' if len(res.text) > 50 else ''}"
        )
        return {"reply": res.text}

    return chat_handler


def create_history_handler(path: str):
    """Create a history handler function for a specific path."""

    async def history_handler(
        user_id: str,
        thread_id: str | None = None,
    ):
        logger.info(f"Fetching conversation history for user {user_id} on path {path}")

        # Get the bot manager and then the bot for this path
        bot_manager = await get_bot_manager()
        runtime = bot_manager.get_bot_for_http_path(path)
        if not runtime:
            raise HTTPException(
                status_code=404, detail=f"No bot configured for path {path}"
            )

        # Get conversation from storage
        if not runtime.store:
            return {"messages": []}

        try:
            # Extract bot_id from path
            bot_id = bot_manager.http_routes.get(path, "default")
            workspace_id = bot_manager.get_workspace_id()

            # Get or create conversation
            conversation = await runtime.store.get_or_create_conversation(
                workspace_id=workspace_id,
                bot_id=bot_id,
                channel_ref="http",
                chat_ref=user_id,
                thread_id=thread_id,
            )

            # Get conversation history
            messages = await runtime.store.get_conversation_history(
                conversation.id, limit=50
            )

            # Filter out tool call requests/results; only show human/assistant conversation
            filtered_messages = []
            for msg in messages:
                meta = msg.message_metadata
                # Exclude explicit tool result messages (OpenAI: role "tool")
                if msg.role == "tool":
                    continue
                # Exclude tool results stored as user messages (Anthropic flow)
                if meta.get("is_tool_result") is True:
                    continue

                # Try to extract user-visible text if content is structured
                visible_text = None
                try:
                    parsed = json.loads(msg.content)
                    if isinstance(parsed, list):
                        texts = [
                            b.get("text", "")
                            for b in parsed
                            if isinstance(b, dict) and b.get("type") == "text"
                        ]
                        visible_text = "\n\n".join(t for t in texts if t)
                except Exception:
                    pass

                # Hide assistant tool-call-only messages (no text blocks)
                if (
                    msg.role == "assistant"
                    and meta.get("tool_calls")
                    and not (visible_text or (msg.content or "").strip())
                ):
                    continue

                # If structured, replace content with extracted text
                if visible_text is not None:
                    msg_for_list = type(msg)(**msg.__dict__)
                    msg_for_list.content = visible_text
                    filtered_messages.append(msg_for_list)
                else:
                    filtered_messages.append(msg)

            # Convert to JSON format for frontend
            history = []
            for msg in filtered_messages:
                history.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat()
                        if msg.created_at
                        else None,
                    }
                )

            return {"messages": history}

        except Exception as e:
            logger.error(f"Error fetching conversation history: {e}")
            return {"messages": []}

    return history_handler


def create_new_chat_handler(path: str):
    """Create a new chat handler function for a specific path."""

    async def new_chat_handler(payload: NewChatIn):
        logger.info(
            f"Creating new conversation for user {payload.user_id} on path {path}"
        )

        # Get the bot manager and then the bot for this path
        bot_manager = await get_bot_manager()
        runtime = bot_manager.get_bot_for_http_path(path)
        if not runtime:
            raise HTTPException(
                status_code=404, detail=f"No bot configured for path {path}"
            )

        if not runtime.store:
            raise HTTPException(
                status_code=500, detail="Storage not configured for this bot"
            )

        try:
            # Extract bot_id from path
            bot_id = bot_manager.http_routes.get(path, "default")
            workspace_id = bot_manager.get_workspace_id()

            # Create a new conversation ID to force a new conversation
            # We do this by using a unique thread_id
            import uuid

            new_thread_id = str(uuid.uuid4())

            # Create new conversation
            conversation = await runtime.store.get_or_create_conversation(
                workspace_id=workspace_id,
                bot_id=bot_id,
                channel_ref="http",
                chat_ref=payload.user_id,
                thread_id=new_thread_id,
            )

            logger.info(f"Created new conversation: {conversation.id}")
            return {
                "conversation_id": conversation.id,
                "thread_id": new_thread_id,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error creating new conversation: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create new conversation: {str(e)}"
            ) from e

    return new_chat_handler


async def register_dynamic_routes(settings=None, bot_manager=None):
    """Register dynamic routes based on bot manager configuration."""
    if bot_manager is None:
        bot_manager = await get_bot_manager(settings=settings)

    for path, bot_id in bot_manager.http_routes.items():
        logger.info(f"Registering HTTP route: {path}")
        handler = create_chat_handler(path)
        route_auth_func = await create_route_auth(path)
        router.add_api_route(
            path, handler, methods=["POST"], dependencies=[Depends(route_auth_func)]
        )

        # Register history endpoint
        history_path = path + "/history"
        logger.info(f"Registering history route: {history_path}")
        history_handler = create_history_handler(path)
        history_auth_func = await create_route_auth(path)  # Use same auth as main route
        router.add_api_route(
            history_path,
            history_handler,
            methods=["GET"],
            dependencies=[Depends(history_auth_func)],
        )

        # Register new chat endpoint
        new_chat_path = path + "/new"
        logger.info(f"Registering new chat route: {new_chat_path}")
        new_chat_handler = create_new_chat_handler(path)
        new_chat_auth_func = await create_route_auth(
            path
        )  # Use same auth as main route
        router.add_api_route(
            new_chat_path,
            new_chat_handler,
            methods=["POST"],
            dependencies=[Depends(new_chat_auth_func)],
        )

        # Also create a UI route for each bot
        ui_path = path.replace("/api/", "/ui/")
        logger.info(f"Registering UI route: {ui_path}")
        ui_handler = create_bot_ui_handler(path, bot_id)
        router.add_api_route(ui_path, ui_handler, methods=["GET"])


def create_bot_ui_handler(path: str, bot_id: str):
    """Create a UI handler function for a specific bot."""

    async def bot_ui_handler():
        """Chat UI for a specific bot"""
        # Get all available bots for navigation
        bot_manager = await get_bot_manager()
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
                white-space: normal; word-wrap: break-word;
            }}
            .user {{ background: #007bff; color: white; margin-left: 20%; }}
            .bot {{ background: #e9ecef; color: #333; margin-right: 20%; }}
            /* Markdown content styling */
            .bot h1, .bot h2, .bot h3 {{ margin: 0.4em 0 0.3em; }}
            .bot p {{ margin: 0.4em 0; }}
            .bot ul, .bot ol {{ margin: 0.4em 1.2em; }}
            .bot code {{ background: #f1f3f5; padding: 2px 4px; border-radius: 4px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; }}
            .bot pre {{ background: #0d1117; color: #e6edf3; padding: 12px; border-radius: 8px; overflow-x: auto; }}
            .bot pre code {{ background: transparent; padding: 0; }}
            .bot blockquote {{ border-left: 4px solid #ced4da; margin: 0.6em 0; padding: 0.2em 0.8em; color: #495057; background: #f8f9fa; }}
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
            .new-chat-btn {{ background: #28a745; margin-left: 10px; }}
            .new-chat-btn:hover {{ background: #218838; }}
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
                <button onclick="newChat()" id="newChatBtn" class="new-chat-btn">New Chat</button>
            </div>
        </div>

        <!-- Lightweight markdown + sanitizer (CDN) -->
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.6/dist/purify.min.js"></script>
        <script>
            const messages = document.getElementById('messages');
            const messageInput = document.getElementById('messageInput');
            const sendBtn = document.getElementById('sendBtn');
            const newChatBtn = document.getElementById('newChatBtn');
            let userId = localStorage.getItem('nexion_user_id') || 'user_' + Date.now();
            let currentThreadId = null; // Track current conversation thread
            localStorage.setItem('nexion_user_id', userId);
            document.getElementById('userId').value = userId;

            function renderMarkdown(mdText) {{
                try {{
                    if (window.marked && window.DOMPurify) {{
                        // Configure marked for GitHub-flavored markdown
                        if (marked && marked.setOptions) {{
                            marked.setOptions({{ gfm: true, breaks: true }})
                        }}
                        const raw = marked.parse(String(mdText || ''));
                        return DOMPurify.sanitize(raw);
                    }}
                }} catch (e) {{
                    console.warn('Markdown render fallback:', e);
                }}
                // Fallback to plain text if libs unavailable
                return String(mdText || '')
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/\\n/g, '<br>');
            }}

            function addMessage(text, isUser = false) {{
                const div = document.createElement('div');
                div.className = `message ${{isUser ? 'user' : 'bot'}}`;
                if (isUser) {{
                    div.textContent = text;
                }} else {{
                    div.innerHTML = renderMarkdown(text);
                }}
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }}

            function clearMessages() {{
                messages.innerHTML = '';
            }}

            function handleEnter(event) {{
                if (event.key === 'Enter' && !event.shiftKey) {{
                    event.preventDefault();
                    sendMessage();
                }}
            }}

            async function loadConversationHistory() {{
                const userId = document.getElementById('userId').value || 'anonymous';
                const apiKey = document.getElementById('apiKey').value;

                try {{
                    const headers = {{}};
                    if (apiKey) {{
                        headers['Authorization'] = `Bearer ${{apiKey}}`;
                    }}

                    let url = '{current_path}/history?user_id=' + encodeURIComponent(userId);
                    if (currentThreadId) {{
                        url += '&thread_id=' + encodeURIComponent(currentThreadId);
                    }}

                    const response = await fetch(url, {{
                        method: 'GET',
                        headers
                    }});

                    if (!response.ok) {{
                        console.error('Failed to load conversation history');
                        return;
                    }}

                    const data = await response.json();
                    clearMessages();

                    if (data.messages && data.messages.length > 0) {{
                        data.messages.forEach(msg => {{
                            addMessage(msg.content, msg.role === 'user');
                        }});
                    }} else {{
                        // Add welcome message if no history
                        addMessage('Hi! I\\'m your {current_bot_id.title()} bot. Ask me anything!');
                    }}

                }} catch (error) {{
                    console.error('Error loading conversation history:', error);
                    addMessage('Hi! I\\'m your {current_bot_id.title()} bot. Ask me anything!');
                }}
            }}

            async function newChat() {{
                const userId = document.getElementById('userId').value || 'anonymous';
                const apiKey = document.getElementById('apiKey').value;

                newChatBtn.disabled = true;
                newChatBtn.textContent = 'Creating...';

                try {{
                    const headers = {{
                        'Content-Type': 'application/json'
                    }};

                    if (apiKey) {{
                        headers['Authorization'] = `Bearer ${{apiKey}}`;
                    }}

                    const response = await fetch('{current_path}/new', {{
                        method: 'POST',
                        headers,
                        body: JSON.stringify({{
                            user_id: userId,
                            bot_id: '{current_bot_id}'
                        }})
                    }});

                    if (!response.ok) {{
                        const error = await response.json();
                        throw new Error(error.detail || `HTTP ${{response.status}}`);
                    }}

                    const data = await response.json();
                    if (data.success) {{
                        currentThreadId = data.thread_id; // Store the new thread ID
                        clearMessages();
                        await loadConversationHistory(); // Reload to reflect fresh state
                        messageInput.focus();
                    }}

                }} catch (error) {{
                    addMessage(`Error creating new chat: ${{error.message}}`, false);
                    console.error('New chat error:', error);
                }}

                newChatBtn.disabled = false;
                newChatBtn.textContent = 'New Chat';
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
                            bot_id: '{current_bot_id}',
                            thread_id: currentThreadId
                        }})
                    }});

                    if (!response.ok) {{
                        const error = await response.json();
                        throw new Error(error.detail || `HTTP ${{response.status}}`);
                    }}

                    await response.json();
                    // After sending, reload entire conversation history to stay in sync
                    await loadConversationHistory();

                }} catch (error) {{
                    addMessage(`Error: ${{error.message}}`, false);
                    console.error('Chat error:', error);
                }}

                sendBtn.disabled = false;
                sendBtn.textContent = 'Send';
                messageInput.focus();
            }}

            // Expose functions to global scope for inline handlers
            window.handleEnter = handleEnter;
            window.sendMessage = sendMessage;
            window.newChat = newChat;

            // Load conversation history when page loads
            document.addEventListener('DOMContentLoaded', function() {{
                loadConversationHistory();
                messageInput.focus();
            }});
        </script>
    </body>
    </html>
    """
    return html


@router.get("/", response_class=HTMLResponse)
async def main_ui():
    """Main UI showing all available bots"""
    bot_manager = await get_bot_manager()
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
