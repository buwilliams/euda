"""
User API Routes

These endpoints maintain backward compatibility with the UI while
internally calling the unified agent functions with agent_id="user".
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ...tools.data.profile import get_profile, update_profile
from ...tools.data.memory import (
    list_memory, add_memory, remove_memory,
    read_long_term_memory, write_long_term_memory, list_long_term_memory_dates
)


router = APIRouter()


class UpdateProfileRequest(BaseModel):
    content: str


class WriteLifelogRequest(BaseModel):
    content: str
    date: Optional[str] = None
    agent: Optional[str] = None


class AddMemoryRequest(BaseModel):
    short_description: str
    type: str
    date_expected: Optional[str] = None


# Profile endpoints
@router.get("/profile")
def api_get_profile():
    """Get user profile."""
    return get_profile("user")


@router.patch("/profile")
def api_update_profile(request: UpdateProfileRequest):
    """Update user profile."""
    return update_profile("user", request.content)


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


# Long-term memory endpoints (lifelog)
@router.get("/lifelog")
def api_get_lifelog(date: Optional[str] = None):
    """Get long-term memory entries."""
    return read_long_term_memory(date, "user")


@router.post("/lifelog")
def api_write_lifelog(request: WriteLifelogRequest):
    """Add a long-term memory entry."""
    return write_long_term_memory(request.content, request.date, "user")


@router.get("/lifelog/dates")
def api_list_dates():
    """List all dates with long-term memory entries."""
    return list_long_term_memory_dates("user")
