"""
System API Routes - Health, about, settings, events
"""

import asyncio
import json
import random
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...tools.jobs import list_jobs


router = APIRouter()

DOCS_DIR = Path(__file__).parent.parent.parent.parent / "docs"


# ============== Health ==============

@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "3.0.0"}


# ============== About ==============

@router.get("/about")
def get_about():
    """Get about/pitch content for the About tab."""
    pitch_file = DOCS_DIR / "1_pitch.md"

    if pitch_file.exists():
        return {"content": pitch_file.read_text()}
    return {"content": "# Euno\n\nPersonal Intelligence System"}


# ============== Daily Quote ==============

QUOTES = [
    {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"quote": "Be yourself; everyone else is already taken.", "author": "Oscar Wilde"},
    {"quote": "The unexamined life is not worth living.", "author": "Socrates"},
    {"quote": "In the middle of difficulty lies opportunity.", "author": "Albert Einstein"},
    {"quote": "What you are is what you have been. What you'll be is what you do now.", "author": "Buddha"},
    {"quote": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb"},
    {"quote": "We suffer more often in imagination than in reality.", "author": "Seneca"},
    {"quote": "The obstacle is the way.", "author": "Marcus Aurelius"},
]


@router.get("/daily-quote")
def daily_quote():
    """Get a daily quote."""
    return random.choice(QUOTES)


# ============== Settings ==============

@router.get("/settings")
def get_settings():
    """Get settings - minimal for v3."""
    return {
        "llm": {
            "default_provider": "anthropic",
            "providers": {
                "anthropic": {"default_model": "claude-sonnet-4-20250514"}
            }
        }
    }


# ============== SSE Events ==============

async def event_generator():
    """Generate SSE events for real-time updates."""
    all_jobs = list_jobs()
    yield f"event: init\ndata: {json.dumps({'jobs': all_jobs})}\n\n"

    while True:
        await asyncio.sleep(30)
        yield f"event: ping\ndata: {{}}\n\n"


@router.get("/events")
async def events():
    """SSE endpoint for real-time updates."""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
