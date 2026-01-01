"""
Context, energy, and queue routes for Euno web API.
"""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ...tools.curator.attention import get_queue, get_recent_energy, record_energy
from ...tools.curator.context import get_context_for_view
from ...tools.curator.daily_quote import get_daily_quote


router = APIRouter(prefix="/api", tags=["context"])


class EnergyRequest(BaseModel):
    physical: Optional[str] = ""
    mental: Optional[str] = ""
    emotional: Optional[str] = ""
    social: Optional[str] = ""
    notes: Optional[str] = ""


@router.get("/context")
async def get_context(view: Optional[str] = None):
    """
    Get aggregated context for the context-first UI.

    Auto-detects appropriate view mode based on time of day:
    - morning (7-10am): Full briefing with schedule, tasks, on-your-mind, noticed
    - active (10am-6pm): Minimal, focus-protecting
    - evening (6-10pm): Reflection with day summary, open threads, tomorrow preview
    - weekly (Sunday): Weekly review
    """
    context = get_context_for_view(view)
    return context


@router.get("/context/morning")
async def get_morning_context():
    """Get morning briefing context."""
    return get_context_for_view("morning")


@router.get("/context/active")
async def get_active_context():
    """Get active day (minimal, focus-protecting) context."""
    return get_context_for_view("active")


@router.get("/context/evening")
async def get_evening_context():
    """Get evening reflection context."""
    return get_context_for_view("evening")


@router.get("/context/weekly")
async def get_weekly_context():
    """Get weekly review context."""
    return get_context_for_view("weekly")


@router.get("/daily-quote")
async def get_daily_quote_endpoint():
    """Get the daily reflection quote."""
    return get_daily_quote()


@router.get("/energy")
async def get_energy(hours: int = 24):
    """Get recent energy readings."""
    content = get_recent_energy(hours)
    return {"content": content}


@router.post("/energy")
async def log_energy(request: EnergyRequest):
    """Record energy reading."""
    result = record_energy(
        physical=request.physical,
        mental=request.mental,
        emotional=request.emotional,
        social=request.social,
        notes=request.notes
    )
    return {"status": "success", "message": result}


@router.get("/queue")
async def get_attention_queue():
    """Get surfacing queue."""
    content = get_queue()
    return {"content": content}
