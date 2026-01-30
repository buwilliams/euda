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
from src.speech import get_speech_client, supports_tts
from ...agent.cognition.metacognition import AgentPausedError, get_token_awareness


router = APIRouter()

# Conversation directory for the user agent (used by web UI)
CONV_DIR = AGENTS_DIR / "user" / "state" / "conversation"


class ChatRequest(BaseModel):
    message: str
    agent_id: str = "user"
    conversation_id: Optional[str] = None
    voice_input: bool = False
    topic_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    agent_id: str
    conversation_id: str
    audio_base64: Optional[str] = None


def get_agent_instance(agent_id: str) -> Agent:
    """Get an agent instance.

    Creates a fresh instance each time to ensure config changes
    are reflected immediately without needing cache invalidation.
    """
    return Agent(agent_id)


@router.post("")
def api_chat(request: ChatRequest) -> ChatResponse:
    """Send a message and get a response."""
    agent = get_agent_instance(request.agent_id)

    # Topic-aware chat session (optional)
    if request.topic_id:
        agent.set_topic_context(request.topic_id)
        if not request.conversation_id:
            request.conversation_id = f"topic-{request.topic_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Set conversation - if None, agent will create a new one on first save
    agent.set_session(request.conversation_id)

    original_get_tools = None
    if request.topic_id:
        # Topic chat should be conversational only (no tool calls or topic state changes)
        agent._topic_chat_mode = True
        original_get_tools = agent._get_tools
        agent._get_tools = lambda: []

    try:
        response = agent.chat(request.message, voice_input=request.voice_input)
    except AgentPausedError as e:
        # Get pause info from token awareness
        token_awareness = get_token_awareness()
        pause_info = token_awareness.get_pause_info(request.agent_id)

        raise HTTPException(
            status_code=503,
            detail={
                "error": "agent_paused",
                "message": f"Agent is paused: {e.reason}. Please resume manually or wait for the next budget period.",
                "reason": e.reason,
                "agent_id": request.agent_id,
                "retry": False
            }
        )
    finally:
        if request.topic_id and original_get_tools:
            agent._get_tools = original_get_tools
            agent._topic_chat_mode = False

    # Emit chat:message_received event for agent triggers
    from ...events import emit_system_event
    from ..events import emit_ui_event
    emit_system_event("chat:message_received", data={"agent_id": request.agent_id})

    # Emit UI event for SSE clients
    emit_ui_event("chat_update", {
        "agent_id": request.agent_id,
        "conversation_id": agent.get_session_id()
    })

    # Append topic chat to asset for persistence/context
    if request.topic_id:
        try:
            from src.core.data.assets import read_asset, write_asset
            from src.core.data.topics import get_topic
            topic = get_topic(request.topic_id)
            topic_name = topic.get("name") if topic else request.topic_id
            timestamp = datetime.now().strftime("%H:%M")
            entry = (
                f"## User ({timestamp})\n\n{request.message}\n\n"
                f"## Assistant ({timestamp})\n\n{response}\n"
            )
            asset_name = f"topic-chat-{request.conversation_id}.md"
            existing = read_asset(request.topic_id, asset_name)
            if existing and existing.get("content"):
                new_content = f"{existing['content'].rstrip()}\n\n{entry}"
            else:
                new_content = f"# Topic Chat — {topic_name}\n\n{entry}"
            write_asset(request.topic_id, asset_name, new_content)
        except Exception:
            # Non-fatal; chat still succeeds
            pass

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
        conversation_id=agent.get_session_id(),
        audio_base64=audio_base64
    )


@router.get("/history")
def api_get_history(agent_id: str = "user", date: Optional[str] = None):
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

        for i, file in enumerate(files):
            conversation_id = file.stem
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

            conv_data = {
                "conversation_id": conversation_id,
                "date": date_str,
                "time": time_str,
                "preview": preview,
                "message_count": message_count
            }
            # Include last_message_timestamp only for the most recent conversation
            if i == 0:
                conv_data["last_message_timestamp"] = int(mtime)

            conversations.append(conv_data)

    return {"conversations": conversations}


class ForkRequest(BaseModel):
    conversation_id: str


@router.post("/conversations/fork")
def fork_conversation(request: ForkRequest):
    """Load a past conversation to continue it."""
    conv_file = CONV_DIR / f"{request.conversation_id}.md"

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
        "new_conversation_id": request.conversation_id,
        "messages": messages
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Delete a conversation by conversation ID."""
    conv_file = CONV_DIR / f"{conversation_id}.md"

    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv_file.unlink()
    return {"status": "deleted", "conversation_id": conversation_id}
