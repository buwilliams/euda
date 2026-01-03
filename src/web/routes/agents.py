"""
Agents API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from ...tools.agents import (
    list_agents, get_agent, get_agent_memory, update_agent_memory,
    get_agent_persona, update_agent_persona, get_agent_config, update_agent_config
)


router = APIRouter()


class UpdateMemoryRequest(BaseModel):
    key: str
    value: str


class UpdatePersonaRequest(BaseModel):
    persona: str


class UpdateConfigRequest(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    tools: Optional[List[str]] = None
    triggers: Optional[List[str]] = None


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


@router.get("/{agent_id}/persona")
def api_get_persona(agent_id: str):
    """Get agent's persona markdown."""
    persona = get_agent_persona(agent_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Agent or persona not found")
    return {"agent_id": agent_id, "persona": persona}


@router.patch("/{agent_id}/persona")
def api_update_persona(agent_id: str, request: UpdatePersonaRequest):
    """Update agent's persona markdown."""
    result = update_agent_persona(agent_id, request.persona)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{agent_id}/config")
def api_get_config(agent_id: str):
    """Get agent's configuration."""
    config = get_agent_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config


@router.patch("/{agent_id}/config")
def api_update_config(agent_id: str, request: UpdateConfigRequest):
    """Update agent's configuration (partial update)."""
    current_config = get_agent_config(agent_id)
    if current_config is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Apply partial updates
    if request.name is not None:
        current_config["name"] = request.name
    if request.enabled is not None:
        current_config["enabled"] = request.enabled
    if request.tools is not None:
        current_config["tools"] = request.tools
    if request.triggers is not None:
        current_config["triggers"] = request.triggers

    result = update_agent_config(agent_id, current_config)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
