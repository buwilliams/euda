"""
User API Routes

These endpoints maintain backward compatibility with the UI while
internally calling the unified agent functions with agent_id="user".
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ...tools.data.identity import get_identity, update_identity
from ...tools.data.memory import (
    list_memory, add_memory, remove_memory, write_long_term_memory
)
from ...agent.rlm import read_memory_date, list_memory_dates


router = APIRouter()


class UpdateIdentityRequest(BaseModel):
    content: str


class WriteMemoryRequest(BaseModel):
    content: str
    date: Optional[str] = None
    agent: Optional[str] = None


class AddMemoryRequest(BaseModel):
    short_description: str
    type: str
    date_expected: Optional[str] = None


# Identity endpoints
@router.get("/identity")
def api_get_identity():
    """Get user identity."""
    return get_identity("user")


@router.patch("/identity")
def api_update_identity(request: UpdateIdentityRequest):
    """Update user identity."""
    return update_identity("user", request.content)


# Short-term memory endpoints
@router.get("/memory")
def api_list_memory():
    """List user's short-term memory items."""
    return list_memory("user")


@router.post("/memory")
def api_add_memory(request: AddMemoryRequest):
    """Add a short-term memory item."""
    return add_memory(request.short_description, request.type, request.date_expected, "user")


@router.delete("/memory/{entry_id}")
def api_remove_memory(entry_id: str):
    """Remove a short-term memory item."""
    return remove_memory(entry_id, "user")


# Long-term memory endpoints
@router.get("/memory/long-term")
def api_get_long_term_memory(date: Optional[str] = None):
    """Get long-term memory entries."""
    if date:
        return read_memory_date("user", date)
    else:
        return {"error": "date parameter required"}


@router.post("/memory/long-term")
def api_write_long_term_memory(request: WriteMemoryRequest):
    """Add a long-term memory entry."""
    return write_long_term_memory(request.content, request.date, "user")


@router.get("/memory/long-term/dates")
def api_list_long_term_dates():
    """List all dates with long-term memory entries."""
    result = list_memory_dates("user")
    # Return just the dates array for backward compatibility with UI
    return result["dates"]
