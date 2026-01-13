"""
Chat API Routes
"""

import base64
import re
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...agent import Agent, AGENTS_DIR
from ...speech import get_speech_client, supports_tts


router = APIRouter()

# Conversation directory for the chat agent (used by web UI)
CONV_DIR = AGENTS_DIR / "chat" / "state" / "conversation"


class ChatRequest(BaseModel):
    message: str
    agent_id: str = "assistant"
    session_id: Optional[str] = None
    voice_input: bool = False


class ChatResponse(BaseModel):
    response: str
    agent_id: str
    session_id: str
    audio_base64: Optional[str] = None


# Cache agent instances
_agents = {}


def get_agent_instance(agent_id: str) -> Agent:
    """Get or create an agent instance."""
    if agent_id not in _agents:
        _agents[agent_id] = Agent(agent_id)
    return _agents[agent_id]


@router.post("")
def api_chat(request: ChatRequest) -> ChatResponse:
    """Send a message and get a response."""
    agent = get_agent_instance(request.agent_id)

    # Set session - if None, agent will create a new one on first save
    agent.set_session(request.session_id)

    response = agent.chat(request.message, voice_input=request.voice_input)

    # Emit chat:message event for agent triggers
    from ...events import emit_event, emit_ui_event
    emit_event("chat:message", data={"agent_id": request.agent_id})

    # Emit UI event for SSE clients
    emit_ui_event("chat_update", {
        "agent_id": request.agent_id,
        "session_id": agent.get_session_id()
    })

    # Generate TTS audio if voice input and TTS available
    audio_base64 = None
    if request.voice_input and supports_tts():
        try:
            client = get_speech_client()
            result = client.synthesize(
                text=response,
                voice="nova",
                instructions="Speak in a warm, friendly, and upbeat tone. Be conversational and personable, like talking to a close friend. Use natural inflections and vary your pacing to sound engaging and approachable."
            )
            audio_base64 = base64.b64encode(result.audio_bytes).decode()
        except Exception as e:
            # TTS failure is non-fatal - just log and continue
            print(f"[Chat] TTS generation failed: {e}")

    return ChatResponse(
        response=response,
        agent_id=request.agent_id,
        session_id=agent.get_session_id(),
        audio_base64=audio_base64
    )


@router.get("/history")
def api_get_history(agent_id: str = "assistant", date: Optional[str] = None):
    """Get conversation history."""
    agent = get_agent_instance(agent_id)

    # Load conversation history
    history = agent._load_conversation_history()

    return {
        "agent_id": agent_id,
        "history": history
    }


# ============== Conversation History (for History tab) ==============

@router.get("/conversations/recent")
def get_recent_conversations(count: int = 20):
    """Get recent conversations for history tab."""
    conversations = []

    if CONV_DIR.exists():
        # Sort by modification time (most recent first)
        files = sorted(CONV_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:count]

        for file in files:
            session_id = file.stem
            content = file.read_text()

            # Use file modification time for display (when conversation was last active)
            mtime = file.stat().st_mtime
            mod_dt = datetime.fromtimestamp(mtime)
            date_str = mod_dt.strftime("%Y-%m-%d")
            time_str = mod_dt.strftime("%H:%M")

            preview = ""
            user_match = re.search(r'## User \([^)]+\)\n\n(.+?)(?:\n\n##|\Z)', content, re.DOTALL)
            if user_match:
                preview = user_match.group(1).strip()[:100]

            message_count = len(re.findall(r'^## (User|Assistant)', content, re.MULTILINE))

            conversations.append({
                "session_id": session_id,
                "date": date_str,
                "time": time_str,
                "preview": preview,
                "message_count": message_count
            })

    return {"conversations": conversations}


class ForkRequest(BaseModel):
    session_id: str


@router.post("/conversations/fork")
def fork_conversation(request: ForkRequest):
    """Load a past conversation to continue it."""
    conv_file = CONV_DIR / f"{request.session_id}.md"

    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    content = conv_file.read_text()
    messages = []

    # Parse markdown format: ## User (HH:MM:SS) or ## Assistant (HH:MM:SS)
    parts = re.split(r'^## (User|Assistant) \([^)]+\)\n\n', content, flags=re.MULTILINE)

    i = 1
    while i < len(parts) - 1:
        role = parts[i].lower()
        msg_content = parts[i + 1].strip()
        if msg_content:
            messages.append({"role": role, "content": msg_content})
        i += 2

    return {
        "new_session_id": request.session_id,
        "messages": messages
    }


@router.delete("/conversations/{session_id}")
def delete_conversation(session_id: str):
    """Delete a conversation by session ID."""
    conv_file = CONV_DIR / f"{session_id}.md"

    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv_file.unlink()
    return {"status": "deleted", "session_id": session_id}
