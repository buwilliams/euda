"""
Agents API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...tools.agents import list_agents, get_agent, get_agent_memory, update_agent_memory


router = APIRouter()


class UpdateMemoryRequest(BaseModel):
    key: str
    value: str


@router.get("")
def api_list_agents():
    """List all agents."""
    return list_agents()


@router.get("/{agent_id}")
def api_get_agent(agent_id: str):
    """Get agent details."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/memory")
def api_get_memory(agent_id: str):
    """Get agent's memory."""
    return get_agent_memory(agent_id)


@router.post("/{agent_id}/memory")
def api_update_memory(agent_id: str, request: UpdateMemoryRequest):
    """Update agent's memory."""
    return update_agent_memory(agent_id, request.key, request.value)
