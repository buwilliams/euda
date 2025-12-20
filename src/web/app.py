"""
me·an·dus - Web API

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
from ..agents.interaction import INTERACTION_TOOLS, INTERACTION_HANDLERS
from ..tools.log import read_log_entry, search_log, get_recent_entries, write_log_entry
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
    title="me·an·dus",
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
        tools=INTERACTION_TOOLS
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
        "name": "me·an·dus",
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
        response = agent.process(request.message, INTERACTION_HANDLERS)

        # Auto-log the conversation
        write_log_entry(
            content=f"**Me:** {request.message}\n\n**Friend:** {response}",
            source="conversation",
            entry_type="chat"
        )

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

# Agent metadata
AGENT_INFO = {
    "ingestion": {"display_name": "Ingestion (Archivist)", "description": "Transforms data into log entries"},
    "interaction": {"display_name": "Interaction (Caring Friend)", "description": "User-facing conversations"},
    "summary": {"display_name": "Summary (Historian)", "description": "Yearly summaries from logs"},
    "values": {"display_name": "Values (Philosopher)", "description": "Derive and refine values"},
    "attention": {"display_name": "Attention (Curator)", "description": "Surface the right thing at the right time"},
    "world": {"display_name": "World (Scout)", "description": "Discover opportunities"},
    "worker": {"display_name": "Worker (Executor)", "description": "Execute approved tasks"},
}

STATE_DIR = BASE_DIR / "data" / "agents" / "state"


def get_agent_state(agent_name: str) -> dict:
    """Load agent state from file if it exists."""
    state_file = STATE_DIR / f"{agent_name}.state.json"
    if state_file.exists():
        with open(state_file, 'r') as f:
            return json.load(f)
    return {}


@app.get("/api/agents/status")
async def get_agent_status():
    """Get status of all agents with real state data."""
    agents = []

    for agent_name, info in AGENT_INFO.items():
        state = get_agent_state(agent_name)

        agent_data = {
            "name": info["display_name"],
            "description": info["description"],
            "status": "ready" if state.get("updated") else "idle",
        }

        # Add state details if available
        if state.get("updated"):
            agent_data["last_active"] = state["updated"]

        # Special handling for interaction agent - show active sessions
        if agent_name == "interaction":
            agent_data["active_sessions"] = len(sessions)

        # Show last work time if available
        if state.get("last_work_time"):
            agent_data["last_work"] = state["last_work_time"]

        # Show work count if available
        if state.get("work_count"):
            agent_data["work_count"] = state["work_count"]

        agents.append(agent_data)

    return {
        "agents": agents,
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


# ============== Notifications ==============

from ..tools.notifications import (
    get_pending_notifications, mark_seen, dismiss_notification,
    check_for_pending_approvals
)


@app.get("/api/notifications")
async def get_notifications(include_seen: bool = False):
    """Get pending notifications for the user."""
    # First, sync approval queues with notifications
    check_for_pending_approvals()

    notifications = get_pending_notifications(include_seen)
    return {
        "notifications": notifications,
        "count": len(notifications),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/notifications/{notification_id}/seen")
async def mark_notification_seen(notification_id: str):
    """Mark a notification as seen."""
    result = mark_seen(notification_id)
    return {"status": "success", "message": result}


@app.post("/api/notifications/{notification_id}/dismiss")
async def dismiss_notification_endpoint(notification_id: str):
    """Dismiss a notification."""
    result = dismiss_notification(notification_id)
    return {"status": "success", "message": result}


# ============== Projects ==============

from ..tools.project import (
    create_project, get_projects, get_project, update_project,
    add_milestone, archive_project, get_projects_with_deadlines
)


class ProjectRequest(BaseModel):
    title: str
    description: str
    project_type: str = "goal"
    priority: str = "normal"
    deadline: Optional[str] = None
    review_frequency: str = "weekly"
    values_alignment: Optional[list] = None


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[str] = None


class MilestoneRequest(BaseModel):
    title: str
    target_date: Optional[str] = None


@app.get("/api/projects")
async def list_projects(status: str = "active", project_type: Optional[str] = None):
    """Get projects."""
    content = get_projects(status=status, project_type=project_type)
    return {"content": content}


@app.get("/api/projects/deadlines")
async def get_upcoming_deadlines(days: int = 7):
    """Get projects with upcoming deadlines."""
    projects = get_projects_with_deadlines(days)
    return {"projects": projects, "days": days}


@app.get("/api/projects/{project_id}")
async def get_project_details(project_id: str):
    """Get project details."""
    content = get_project(project_id)
    return {"content": content}


@app.post("/api/projects")
async def create_new_project(request: ProjectRequest):
    """Create a new project."""
    result = create_project(
        title=request.title,
        description=request.description,
        project_type=request.project_type,
        priority=request.priority,
        deadline=request.deadline,
        review_frequency=request.review_frequency,
        values_alignment=request.values_alignment
    )
    return {"status": "success", "message": result}


@app.put("/api/projects/{project_id}")
async def update_project_details(project_id: str, request: ProjectUpdateRequest):
    """Update a project."""
    result = update_project(
        project_id=project_id,
        title=request.title,
        description=request.description,
        status=request.status,
        priority=request.priority,
        deadline=request.deadline
    )
    return {"status": "success", "message": result}


@app.post("/api/projects/{project_id}/milestones")
async def add_project_milestone(project_id: str, request: MilestoneRequest):
    """Add a milestone to a project."""
    result = add_milestone(project_id, request.title, request.target_date)
    return {"status": "success", "message": result}


@app.post("/api/projects/{project_id}/archive")
async def archive_project_endpoint(project_id: str):
    """Archive a project."""
    result = archive_project(project_id)
    return {"status": "success", "message": result}


# ============== Tasks ==============

from ..tools.task import (
    create_task, create_learning_task, get_tasks, get_task,
    get_daily_view, add_quick_task, update_task_status,
    get_recent_results, get_result
)


class TaskRequest(BaseModel):
    description: str
    task_type: str = "general"
    project_id: Optional[str] = None
    priority: str = "normal"
    due_date: Optional[str] = None


class LearningTaskRequest(BaseModel):
    description: str
    project_id: Optional[str] = None
    learning_objectives: Optional[list] = None
    preferred_format: str = "mixed"


class QuickTaskRequest(BaseModel):
    description: str


@app.get("/api/tasks")
async def list_tasks(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50
):
    """Get tasks with optional filters."""
    content = get_tasks(
        status=status,
        project_id=project_id,
        priority=priority,
        limit=limit
    )
    return {"content": content}


@app.get("/api/tasks/daily")
async def get_todays_tasks(date: Optional[str] = None):
    """Get daily task view."""
    content = get_daily_view(date)
    return {"content": content}


@app.get("/api/tasks/{task_id}")
async def get_task_details(task_id: str):
    """Get task details."""
    from ..tools.task import get_task as get_task_detail
    content = get_task_detail(task_id)
    return {"content": content}


@app.post("/api/tasks")
async def create_new_task(request: TaskRequest):
    """Create a new task."""
    result = create_task(
        description=request.description,
        task_type=request.task_type,
        project_id=request.project_id,
        priority=request.priority,
        due_date=request.due_date,
        source_agent="api"
    )
    return {"status": "success", "message": result}


@app.post("/api/tasks/learning")
async def create_new_learning_task(request: LearningTaskRequest):
    """Create a learning task."""
    result = create_learning_task(
        description=request.description,
        project_id=request.project_id,
        learning_objectives=request.learning_objectives,
        preferred_format=request.preferred_format
    )
    return {"status": "success", "message": result}


@app.post("/api/tasks/quick")
async def add_new_quick_task(request: QuickTaskRequest):
    """Add a quick ad-hoc task for today."""
    result = add_quick_task(request.description)
    return {"status": "success", "message": result}


@app.put("/api/tasks/{task_id}/status")
async def update_task_status_endpoint(task_id: str, status: str):
    """Update task status."""
    result = update_task_status(task_id, status)
    return {"status": "success", "message": result}


# ============== Results ==============

@app.get("/api/results")
async def list_results(project_id: Optional[str] = None, limit: int = 10):
    """Get recent results."""
    content = get_recent_results(project_id=project_id, limit=limit)
    return {"content": content}


@app.get("/api/results/{result_id}")
async def get_result_details(result_id: str):
    """Get result details."""
    content = get_result(result_id)
    return {"content": content}


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
