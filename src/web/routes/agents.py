"""
Agents API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ...tools.agents.agents import (
    list_agents, get_agent,
    get_agent_profile, update_agent_profile,
    get_agent_config, update_agent_config
)
from ...tools.data.profile import get_profile, update_profile
from ...tools.data.memory import (
    list_memory, add_memory, remove_memory,
    read_long_term_memory, write_long_term_memory, list_long_term_memory_dates
)


router = APIRouter()


class UpdateProfileRequest(BaseModel):
    content: str


class UpdateConfigRequest(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    tools: Optional[List[str]] = None
    triggers: Optional[List[str]] = None


class AddMemoryRequest(BaseModel):
    short_description: str
    type: str
    date_expected: Optional[str] = None


class WriteLongTermMemoryRequest(BaseModel):
    content: str
    date: Optional[str] = None


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


# Profile endpoints
@router.get("/{agent_id}/profile")
def api_get_profile(agent_id: str):
    """Get agent's profile markdown."""
    profile = get_agent_profile(agent_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Agent or profile not found")
    return {"agent_id": agent_id, "profile": profile}


@router.patch("/{agent_id}/profile")
def api_update_profile(agent_id: str, request: UpdateProfileRequest):
    """Update agent's profile markdown."""
    result = update_agent_profile(agent_id, request.content)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Backward-compatible persona endpoints (alias to profile)
@router.get("/{agent_id}/persona")
def api_get_persona(agent_id: str):
    """Get agent's persona markdown (alias for profile)."""
    profile = get_agent_profile(agent_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Agent or persona not found")
    return {"agent_id": agent_id, "persona": profile}


@router.patch("/{agent_id}/persona")
def api_update_persona(agent_id: str, request: UpdateProfileRequest):
    """Update agent's persona markdown (alias for profile)."""
    result = update_agent_profile(agent_id, request.content)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Config endpoints
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


# Short-term memory endpoints
@router.get("/{agent_id}/memory/short-term")
def api_get_short_term_memory(agent_id: str):
    """List agent's short-term memory items."""
    return list_memory(agent_id)


@router.post("/{agent_id}/memory/short-term")
def api_add_short_term_memory(agent_id: str, request: AddMemoryRequest):
    """Add a short-term memory item."""
    return add_memory(request.short_description, request.type, request.date_expected, agent_id)


@router.delete("/{agent_id}/memory/short-term/{entry_id}")
def api_remove_short_term_memory(agent_id: str, entry_id: str):
    """Remove a short-term memory item."""
    return remove_memory(entry_id, agent_id)


# Long-term memory endpoints
@router.get("/{agent_id}/memory/long-term")
def api_get_long_term_memory(agent_id: str, date: Optional[str] = None):
    """Get agent's long-term memory entries."""
    return read_long_term_memory(date, agent_id)


@router.post("/{agent_id}/memory/long-term")
def api_write_long_term_memory(agent_id: str, request: WriteLongTermMemoryRequest):
    """Add a long-term memory entry."""
    return write_long_term_memory(request.content, request.date, agent_id)


@router.get("/{agent_id}/memory/long-term/dates")
def api_list_long_term_memory_dates(agent_id: str):
    """List all dates with long-term memory entries."""
    return list_long_term_memory_dates(agent_id)
