"""
User API Routes
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ...tools.user import (
    get_user_profile, update_user_profile,
    read_lifelog, write_lifelog, list_lifelog_dates
)


router = APIRouter()


class UpdateProfileRequest(BaseModel):
    content: str


class WriteLifelogRequest(BaseModel):
    content: str
    date: Optional[str] = None


@router.get("/profile")
def api_get_profile():
    """Get user profile."""
    return get_user_profile()


@router.patch("/profile")
def api_update_profile(request: UpdateProfileRequest):
    """Update user profile."""
    return update_user_profile(request.content)


@router.get("/lifelog")
def api_get_lifelog(date: Optional[str] = None):
    """Get lifelog entries."""
    return read_lifelog(date)


@router.post("/lifelog")
def api_write_lifelog(request: WriteLifelogRequest):
    """Add a lifelog entry."""
    return write_lifelog(request.content, request.date)


@router.get("/lifelog/dates")
def api_list_dates():
    """List all dates with lifelog entries."""
    return list_lifelog_dates()
