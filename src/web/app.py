"""
Me and Us - Web API

FastAPI application for the Interaction Agent and other endpoints.
"""

import uuid
import json
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..agents.base import create_agent
from ..tools.log import LOG_TOOLS, LOG_HANDLERS, read_log_entry, search_log, get_recent_entries
from ..tools.values import get_current_values, get_phase_values, get_lifetime_values, get_all_values
from ..tools.cards import (
    get_internal_card, get_public_card, write_public_card,
    get_received_cards, update_received_card_status, approve_public_card
)
from ..tools.world import get_opportunities
from ..tools.attention import get_queue, get_recent_energy, record_energy
from ..tools.summary import list_years, get_summary


# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
STATIC_DIR = BASE_DIR / "static"

# Initialize FastAPI app
app = FastAPI(
    title="Me and Us",
    description="AI Personal Assistant API",
    version="0.1.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Session storage (in-memory for now)
sessions: dict = {}


# ============== Request/Response Models ==============

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


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


class EnergyRequest(BaseModel):
    physical: Optional[str] = ""
    mental: Optional[str] = ""
    emotional: Optional[str] = ""
    social: Optional[str] = ""
    notes: Optional[str] = ""


# ============== Session Helpers ==============

def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, object]:
    """Get an existing session or create a new one."""
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]["agent"]

    new_id = session_id or str(uuid.uuid4())
    agent = create_agent(
        persona_name="interaction",
        tools=LOG_TOOLS
    )

    sessions[new_id] = {
        "agent": agent,
        "created": datetime.now(),
        "last_used": datetime.now()
    }

    return new_id, agent


# ============== Root & Static ==============

@app.get("/")
async def root():
    """Serve the main page or API info."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "Me and Us",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/app")
async def app_page():
    """Serve the main app page."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="App not found. Run from project root.")


# ============== Chat ==============

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the Interaction Agent."""
    session_id, agent = get_or_create_session(request.session_id)

    try:
        sessions[session_id]["last_used"] = datetime.now()
        response = agent.process(request.message, LOG_HANDLERS)

        return ChatResponse(
            response=response,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Keep old endpoint for compatibility
@app.post("/chat", response_model=ChatResponse)
async def chat_legacy(request: ChatRequest):
    return await chat(request)


# ============== Logs ==============

@app.get("/api/logs/{date}")
async def get_log(date: str):
    """Get log entries for a specific date."""
    content = read_log_entry(date)
    return {"date": date, "content": content}


@app.post("/api/logs/search")
async def search_logs(request: LogSearchRequest):
    """Search log entries."""
    results = search_log(query=request.query, year=request.year, limit=request.limit)
    return {"query": request.query, "results": results}


@app.get("/api/logs/recent")
async def get_recent(days: int = 7):
    """Get recent log entries."""
    content = get_recent_entries(days)
    return {"days": days, "content": content}


# ============== Values ==============

@app.get("/api/values")
async def get_values():
    """Get all values."""
    return {
        "current": get_current_values(),
        "phase": get_phase_values(),
        "lifetime": get_lifetime_values()
    }


@app.get("/api/values/current")
async def get_current():
    """Get current values."""
    return {"content": get_current_values()}


@app.get("/api/values/phase")
async def get_phase():
    """Get phase values."""
    return {"content": get_phase_values()}


@app.get("/api/values/lifetime")
async def get_lifetime():
    """Get lifetime values."""
    return {"content": get_lifetime_values()}


# ============== Cards ==============

@app.get("/api/cards/internal")
async def get_internal():
    """Get internal value card."""
    content = get_internal_card()
    try:
        return {"card": json.loads(content)}
    except json.JSONDecodeError:
        return {"card": None, "message": content}


@app.get("/api/cards/public")
async def get_public():
    """Get public value card."""
    content = get_public_card()
    try:
        return {"card": json.loads(content)}
    except json.JSONDecodeError:
        return {"card": None, "message": content}


@app.put("/api/cards/public")
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


@app.post("/api/cards/public/approve")
async def approve_card():
    """Approve public card for sharing."""
    result = approve_public_card()
    return {"status": "success", "message": result}


@app.get("/api/cards/received")
async def get_received(status: Optional[str] = None):
    """Get received cards."""
    content = get_received_cards(status or "")
    return {"content": content}


@app.put("/api/cards/received/{from_agent}/status")
async def update_card_status(from_agent: str, new_status: str):
    """Update received card status."""
    result = update_received_card_status(from_agent, new_status)
    return {"status": "success", "message": result}


# ============== Opportunities ==============

@app.get("/api/opportunities")
async def get_opps(category: Optional[str] = None, alignment: Optional[str] = None):
    """Get discovered opportunities."""
    content = get_opportunities(category=category or "", alignment=alignment or "")
    return {"content": content}


# ============== Energy ==============

@app.get("/api/energy")
async def get_energy(hours: int = 24):
    """Get recent energy readings."""
    content = get_recent_energy(hours)
    return {"content": content}


@app.post("/api/energy")
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


# ============== Attention Queue ==============

@app.get("/api/queue")
async def get_attention_queue():
    """Get surfacing queue."""
    content = get_queue()
    return {"content": content}


# ============== Summaries ==============

@app.get("/api/summaries")
async def get_summaries_list():
    """List years with summaries."""
    content = list_years()
    return {"content": content}


@app.get("/api/summaries/{year}")
async def get_year_summary(year: int):
    """Get summary for a year."""
    content = get_summary(year)
    return {"year": year, "content": content}


# ============== Agent Status ==============

@app.get("/api/agents/status")
async def get_agent_status():
    """Get status of all agents."""
    # Simple status based on file existence
    data_dir = BASE_DIR / "data"

    return {
        "agents": [
            {
                "name": "Ingestion (Archivist)",
                "status": "available",
                "description": "Transforms data into log entries"
            },
            {
                "name": "Interaction (Caring Friend)",
                "status": "available",
                "active_sessions": len(sessions),
                "description": "User-facing conversations"
            },
            {
                "name": "Summary (Historian)",
                "status": "available",
                "description": "Yearly summaries from logs"
            },
            {
                "name": "Values (Philosopher)",
                "status": "available",
                "description": "Derive and refine values"
            },
            {
                "name": "Attention (Curator)",
                "status": "available",
                "description": "Surface the right thing at the right time"
            },
            {
                "name": "World (Scout)",
                "status": "available",
                "description": "Discover opportunities"
            }
        ],
        "timestamp": datetime.now().isoformat()
    }


# ============== Sessions ==============

@app.get("/api/sessions")
async def list_sessions():
    """List active sessions."""
    return {
        "count": len(sessions),
        "sessions": [
            {
                "id": sid,
                "created": s["created"].isoformat(),
                "last_used": s["last_used"].isoformat()
            }
            for sid, s in sessions.items()
        ]
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


# ============== Health ==============

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Legacy endpoints for compatibility
@app.get("/logs/{date}")
async def get_log_legacy(date: str):
    return await get_log(date)


@app.get("/health")
async def health_legacy():
    return await health_check()
