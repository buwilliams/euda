"""
Chat API Routes
"""

import re
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ...agent import Agent, AGENTS_DIR


router = APIRouter()


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
