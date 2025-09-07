from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from ..config.bridge import get_settings_from_yaml
from ..core.types import MessageEvent, Channel
from ..core.agent import AgentRuntime
from ..config.settings import Settings
from nexion.utils.logging import get_logger

router = APIRouter()
logger = get_logger("http")


class ChatIn(BaseModel):
    bot_id: str = "default"
    user_id: str
    message: str
    thread_id: Optional[str] = None


def auth(
    settings: Settings = Depends(get_settings_from_yaml),
    authorization: Optional[str] = Header(None),
):
    if not settings.BOT_HTTP_KEY:
        raise HTTPException(status_code=500, detail="Bot HTTP key not set")
    if settings.BOT_HTTP_KEY and authorization != f"Bearer {settings.BOT_HTTP_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return settings


@router.post("/api/chat")
async def chat(payload: ChatIn, settings: Settings = Depends(auth)):
    logger.info(
        f"Processing chat request from user {payload.user_id}: {payload.message[:50]}{'...' if len(payload.message) > 50 else ''}"
    )

    runtime = AgentRuntime(settings)
    await runtime.initialize()

    event = MessageEvent(
        channel=Channel.HTTP,
        user_id=payload.user_id,
        text=payload.message,
        bot_id=payload.bot_id,
        workspace_id="default",  # TODO: Make this configurable
        thread_id=payload.thread_id,
    )
    res = await runtime.handle(event)

    logger.info(
        f"Sent reply to user {payload.user_id}: {res.text[:50]}{'...' if len(res.text) > 50 else ''}"
    )
    return {"reply": res.text}


@router.get("/", response_class=HTMLResponse)
async def chat_ui():
    """Simple chat UI for testing the bot"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nexion Bot Chat</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px; margin: 0 auto; padding: 20px; 
                background: #f5f5f5;
            }
            .chat-container {
                background: white; border-radius: 12px; padding: 20px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .messages { 
                height: 400px; overflow-y: auto; border: 1px solid #ddd; 
                padding: 15px; margin: 15px 0; border-radius: 8px;
                background: #fafafa;
            }
            .message { 
                margin: 10px 0; padding: 8px 12px; border-radius: 8px; 
            }
            .user { background: #007bff; color: white; margin-left: 20%; }
            .bot { background: #e9ecef; color: #333; margin-right: 20%; }
            .input-group { display: flex; gap: 10px; }
            input { 
                flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 8px;
                font-size: 16px;
            }
            button { 
                padding: 12px 20px; background: #007bff; color: white; 
                border: none; border-radius: 8px; cursor: pointer; font-size: 16px;
            }
            button:hover { background: #0056b3; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 6px; margin: 10px 0; }
            .settings { margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
            .settings input { flex: none; width: 200px; }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <h1>🤖 Nexion Bot Chat</h1>
            
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
            
            function addMessage(text, isUser = false) {
                const div = document.createElement('div');
                div.className = `message ${isUser ? 'user' : 'bot'}`;
                div.textContent = text;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }
            
            function handleEnter(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                }
            }
            
            async function sendMessage() {
                const message = messageInput.value.trim();
                if (!message) return;
                
                const userId = document.getElementById('userId').value || 'anonymous';
                const apiKey = document.getElementById('apiKey').value;
                
                addMessage(message, true);
                messageInput.value = '';
                sendBtn.disabled = true;
                sendBtn.textContent = 'Sending...';
                
                try {
                    const headers = {
                        'Content-Type': 'application/json'
                    };
                    
                    if (apiKey) {
                        headers['Authorization'] = `Bearer ${apiKey}`;
                    }
                    
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers,
                        body: JSON.stringify({
                            user_id: userId,
                            message: message,
                            bot_id: 'default'
                        })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || `HTTP ${response.status}`);
                    }
                    
                    const data = await response.json();
                    addMessage(data.reply);
                    
                } catch (error) {
                    addMessage(`Error: ${error.message}`, false);
                    console.error('Chat error:', error);
                }
                
                sendBtn.disabled = false;
                sendBtn.textContent = 'Send';
                messageInput.focus();
            }
            
            // Focus on input when page loads
            messageInput.focus();
            
            // Add welcome message
            addMessage('Hi! I\\'m your Nexion bot. Ask me anything!');
        </script>
    </body>
    </html>
    """
    return html


# Log when the HTTP router is imported
logger.info("HTTP adapter initialized - /api/chat endpoint and UI available at /")
