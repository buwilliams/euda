"""
Chat API Routes
"""

import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...agent import Agent, AGENTS_DIR


router = APIRouter()

# Conversation directory for the friend agent (used by web UI)
CONV_DIR = AGENTS_DIR / "friend" / "state" / "conversation"


class ChatRequest(BaseModel):
    message: str
    agent_id: str = "assistant"


class ChatResponse(BaseModel):
    response: str
    agent_id: str


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
    response = agent.chat(request.message)

    return ChatResponse(
        response=response,
        agent_id=request.agent_id
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
        files = sorted(CONV_DIR.glob("*.md"), reverse=True)[:count]

        for file in files:
            date_str = file.stem
            content = file.read_text()

            # Extract first timestamp and preview
            time_match = re.search(r'\((\d{2}:\d{2}):\d{2}\)', content)
            time_str = time_match.group(1) if time_match else "00:00"

            preview = ""
            user_match = re.search(r'## User \([^)]+\)\n\n(.+?)(?:\n\n##|\Z)', content, re.DOTALL)
            if user_match:
                preview = user_match.group(1).strip()[:100]

            message_count = len(re.findall(r'^## (User|Assistant)', content, re.MULTILINE))

            conversations.append({
                "session_id": date_str,
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
