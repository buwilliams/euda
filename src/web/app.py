"""
FastAPI Web Application

Provides REST API for the Euno system.
"""

import asyncio
import json
import random
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pathlib import Path

from .routes import jobs, agents, chat, user
from ..tools.jobs import list_jobs


app = FastAPI(
    title="Euno",
    description="Personal Intelligence System",
    version="3.0.0"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(user.router, prefix="/api/user", tags=["user"])


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "3.0.0"}


# ============== Auth (simplified) ==============

@app.get("/api/auth/check")
def auth_check():
    """Check authentication - always returns authenticated for v3."""
    return {"authenticated": True, "password_required": False}


@app.post("/api/auth/login")
def auth_login():
    """Login - always succeeds for v3."""
    return {"success": True}


@app.post("/api/auth/logout")
def auth_logout():
    """Logout - no-op for v3."""
    return {"success": True}


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


@app.get("/api/daily-quote")
def daily_quote():
    """Get a daily quote."""
    return random.choice(QUOTES)


# ============== SSE Events ==============

async def event_generator():
    """Generate SSE events for real-time updates."""
    # Send initial data
    all_jobs = list_jobs()
    yield f"event: init\ndata: {json.dumps({'jobs': all_jobs})}\n\n"

    # Keep connection alive with pings
    while True:
        await asyncio.sleep(30)
        yield f"event: ping\ndata: {{}}\n\n"


@app.get("/api/events")
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


# ============== Settings (simplified) ==============

@app.get("/api/settings")
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


# Serve static files (must be last)
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
