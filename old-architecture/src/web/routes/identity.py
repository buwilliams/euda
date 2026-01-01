"""
Identity, cards, logs, and summaries routes for Euno web API.
"""

import json
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ...tools.profiler import get_profile, get_synthesis_summary
from ...tools.profiler.summary import list_years, get_summary
from ...tools.friend.cards import (
    get_internal_card, get_public_card, write_public_card,
    get_received_cards, update_received_card_status, approve_public_card
)
from ...tools.shared.log import read_log_entry, search_log, get_recent_entries


router = APIRouter(prefix="/api", tags=["identity"])


class LogSearchRequest(BaseModel):
    query: str
    year: Optional[int] = None
    limit: Optional[int] = 10


class PublicCardRequest(BaseModel):
    display_name: str
    values_summary: str
    interests: list
    open_to: list
    not_interested: Optional[list] = None
    contact_preferences: Optional[dict] = None


# Identity routes

@router.get("/identity")
async def get_identity():
    """Get full identity profile (unified behavioral model)."""
    return {
        "profile": get_profile(),
        "summary": get_synthesis_summary()
    }


@router.get("/identity/summary")
async def get_synthesis_summary_endpoint():
    """Get quick synthesis summary."""
    return {"content": get_synthesis_summary()}


@router.get("/identity/profile")
async def get_identity_profile():
    """Get the unified identity profile."""
    return {"content": get_profile()}


# Cards routes

@router.get("/cards/internal")
async def get_internal():
    """Get internal value card."""
    content = get_internal_card()
    try:
        return {"card": json.loads(content)}
    except json.JSONDecodeError:
        return {"card": None, "message": content}


@router.get("/cards/public")
async def get_public():
    """Get public value card."""
    content = get_public_card()
    try:
        return {"card": json.loads(content)}
    except json.JSONDecodeError:
        return {"card": None, "message": content}


@router.put("/cards/public")
async def update_public(request: PublicCardRequest):
    """Update public value card."""
    result = write_public_card(
        display_name=request.display_name,
        values_summary=request.values_summary,
        interests=request.interests,
        open_to=request.open_to,
        not_interested=request.not_interested,
        contact_preferences=request.contact_preferences
    )
    return {"status": "success", "message": result}


@router.post("/cards/public/approve")
async def approve_card():
    """Approve public card for sharing."""
    result = approve_public_card()
    return {"status": "success", "message": result}


@router.get("/cards/received")
async def get_received(status: Optional[str] = None):
    """Get received cards."""
    content = get_received_cards(status or "")
    return {"content": content}


@router.put("/cards/received/{from_agent}/status")
async def update_card_status(from_agent: str, new_status: str):
    """Update received card status."""
    result = update_received_card_status(from_agent, new_status)
    return {"status": "success", "message": result}


# Logs routes

@router.get("/logs/{date}")
async def get_log(date: str):
    """Get log entries for a specific date."""
    content = read_log_entry(date)
    return {"date": date, "content": content}


@router.post("/logs/search")
async def search_logs(request: LogSearchRequest):
    """Search log entries."""
    results = search_log(query=request.query, year=request.year, limit=request.limit)
    return {"query": request.query, "results": results}


@router.get("/logs/recent")
async def get_recent(days: int = 7):
    """Get recent log entries."""
    content = get_recent_entries(days)
    return {"days": days, "content": content}


# Summaries routes

@router.get("/summaries")
async def get_summaries_list():
    """List years with summaries."""
    content = list_years()
    return {"content": content}


@router.get("/summaries/{year}")
async def get_year_summary(year: int):
    """Get summary for a year."""
    content = get_summary(year)
    return {"year": year, "content": content}
