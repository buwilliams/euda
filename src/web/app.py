"""
Euno - Web API

FastAPI application for the Interaction Agent and other endpoints.
SSE support for real-time updates.
"""

import uuid
import json
import asyncio
from datetime import datetime
from typing import Optional, List
from pathlib import Path
from contextlib import asynccontextmanager

import re
import aiofiles
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from watchfiles import awatch, Change

from ..agents.base import create_agent
from ..agents.interaction import INTERACTION_TOOLS, INTERACTION_HANDLERS
from ..tools.shared.log import read_log_entry, search_log, get_recent_entries, write_log_entry
from ..tools.interaction.conversation_history import save_message, get_conversation_data, get_recent_conversations
from ..tools.synthesis import get_profile, get_synthesis_summary
from ..tools.interaction.cards import (
    get_internal_card, get_public_card, write_public_card,
    get_received_cards, update_received_card_status, approve_public_card
)
from ..tools.world.world import get_opportunities
from ..tools.attention.attention import get_queue, get_recent_energy, record_energy
from ..tools.attention.context import get_context_for_view, get_view_mode
from ..tools.synthesis.summary import list_years, get_summary


# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
INBOX_PENDING_DIR = BASE_DIR / "data" / "ingestion" / "state" / "inbox" / "pending"


# ============== SSE Event Manager ==============

class SSEManager:
    """Manages Server-Sent Events for real-time updates."""

    def __init__(self):
        self.queues: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        """Create a new subscription queue."""
        queue = asyncio.Queue()
        self.queues.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Remove a subscription queue."""
        if queue in self.queues:
            self.queues.remove(queue)

    async def broadcast(self, event_type: str, data: dict):
        """Send event to all subscribers."""
        message = {"event": event_type, "data": data}
        for queue in list(self.queues):
            try:
                await queue.put(message)
            except Exception:
                pass


sse_manager = SSEManager()


# ============== Background Tasks ==============

async def watch_tasks():
    """Watch tasks queue and broadcast changes via SSE."""
    tasks_dir = BASE_DIR / "data" / "worker" / "state" / "tasks"
    queue_file = tasks_dir / "queue.json"

    if not tasks_dir.exists():
        tasks_dir.mkdir(parents=True, exist_ok=True)

    last_mtime = None

    async for changes in awatch(tasks_dir):
        # Check if queue.json was modified
        if queue_file.exists():
            current_mtime = queue_file.stat().st_mtime
            if current_mtime != last_mtime:
                last_mtime = current_mtime
                # Broadcast task update
                tasks = get_tasks_for_panel()
                await sse_manager.broadcast("tasks_update", {"tasks": tasks})


async def watch_projects():
    """Watch projects directory and broadcast changes via SSE."""
    projects_dir = BASE_DIR / "data" / "worker" / "state" / "projects"

    if not projects_dir.exists():
        projects_dir.mkdir(parents=True, exist_ok=True)

    async for changes in awatch(projects_dir):
        # Broadcast projects update on any change
        projects = get_projects_data(status="active")
        await sse_manager.broadcast("projects_update", {"projects": projects})


# ============== Lifespan Management ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage background tasks on startup/shutdown."""
    # Start background tasks
    tasks_watcher_task = asyncio.create_task(watch_tasks())
    projects_watcher_task = asyncio.create_task(watch_projects())

    yield

    # Cancel tasks on shutdown
    tasks_watcher_task.cancel()
    projects_watcher_task.cancel()


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Euno",
    description="AI Personal Assistant API",
    version="0.1.0",
    lifespan=lifespan
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
    clear_chat: bool = False


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
        "name": "Euno",
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
    from ..tools.interaction.conversation import reset_clear_flag, was_clear_requested

    session_id, agent = get_or_create_session(request.session_id)

    try:
        # Reset the clear flag before processing
        reset_clear_flag()

        sessions[session_id]["last_used"] = datetime.now()
        response = agent.process(request.message, INTERACTION_HANDLERS)

        # Check if clear_conversation tool was called during processing
        clear_chat = was_clear_requested()

        if clear_chat:
            # Clear the agent's context
            agent.clear_context()
            # Create a fresh session
            new_session_id = str(uuid.uuid4())
            sessions[new_session_id] = {
                "agent": create_agent("interaction", INTERACTION_TOOLS),
                "created": datetime.now(),
                "last_used": datetime.now()
            }
            session_id = new_session_id

        # Auto-log the conversation (skip if clearing)
        if not clear_chat:
            write_log_entry(
                content=f"**Me:** {request.message}\n\n**Friend:** {response}",
                source="conversation",
                entry_type="chat"
            )
            # Also save to conversation history for retrieval
            save_message(
                session_id=session_id,
                user_message=request.message,
                assistant_response=response
            )

        return ChatResponse(
            response=response,
            session_id=session_id,
            clear_chat=clear_chat
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


# ============== Identity ==============

@app.get("/api/identity")
async def get_identity():
    """Get full identity profile (unified behavioral model)."""
    return {
        "profile": get_profile(),
        "summary": get_synthesis_summary()
    }


@app.get("/api/identity/summary")
async def get_synthesis_summary_endpoint():
    """Get quick synthesis summary."""
    return {"content": get_synthesis_summary()}


@app.get("/api/identity/profile")
async def get_identity_profile():
    """Get the unified identity profile."""
    return {"content": get_profile()}


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


# ============== Context (Context-First UI) ==============

@app.get("/api/context")
async def get_context(view: Optional[str] = None):
    """
    Get aggregated context for the context-first UI.

    Auto-detects appropriate view mode based on time of day:
    - morning (7-10am): Full briefing with schedule, tasks, on-your-mind, noticed
    - active (10am-6pm): Minimal, focus-protecting
    - evening (6-10pm): Reflection with day summary, open threads, tomorrow preview
    - weekly (Sunday): Weekly review

    Args:
        view: Optional override for view mode
    """
    context = get_context_for_view(view)
    return context


@app.get("/api/context/morning")
async def get_morning_context():
    """Get morning briefing context."""
    return get_context_for_view("morning")


@app.get("/api/context/active")
async def get_active_context():
    """Get active day (minimal, focus-protecting) context."""
    return get_context_for_view("active")


@app.get("/api/context/evening")
async def get_evening_context():
    """Get evening reflection context."""
    return get_context_for_view("evening")


@app.get("/api/context/weekly")
async def get_weekly_context():
    """Get weekly review context."""
    return get_context_for_view("weekly")


# ============== Daily Quote ==============

@app.get("/api/daily-quote")
async def get_daily_quote_endpoint():
    """Get the daily reflection quote."""
    from src.tools.attention.daily_quote import get_daily_quote
    return get_daily_quote()


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
    "synthesis": {"display_name": "Synthesis (Keeper)", "description": "Synthesizes user identity from patterns"},
    "attention": {"display_name": "Attention (Curator)", "description": "Surface the right thing at the right time"},
    "world": {"display_name": "World (Scout)", "description": "Discover opportunities"},
    "worker": {"display_name": "Worker (Executor)", "description": "Execute approved tasks"},
    "evolution": {"display_name": "Evolution (Evolver)", "description": "Evolves agent identities based on synthesis"},
}

def get_agent_state(agent_name: str) -> dict:
    """Load agent state from file if it exists."""
    # Each agent now has its own state directory
    state_file = BASE_DIR / "data" / agent_name / "state" / "state.json"
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

        # Determine status more accurately
        status = "idle"
        if state.get("updated"):
            status = "ready"
        if state.get("currently_processing"):
            status = "working"

        agent_data = {
            "name": info["display_name"],
            "description": info["description"],
            "status": status,
        }

        # Add state details if available
        if state.get("updated"):
            agent_data["last_active"] = state["updated"]

        # Special handling for interaction agent - show active sessions
        if agent_name == "interaction":
            agent_data["active_sessions"] = len(sessions)

        # Special handling for ingestion - show queue info
        if agent_name == "ingestion":
            pending_dir = BASE_DIR / "data" / "ingestion" / "state" / "inbox" / "pending"
            if pending_dir.exists():
                pending_count = len([f for f in pending_dir.iterdir() if f.is_file() and not f.name.startswith('.')])
                agent_data["pending_files"] = pending_count
                if pending_count > 0:
                    agent_data["status"] = "working"
            if state.get("current_file"):
                agent_data["current_file"] = state["current_file"]

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


# ============== Conversation History ==============

@app.get("/api/conversations/recent")
async def get_recent_convos(count: int = 5):
    """Get recent conversations with previews."""
    content = get_recent_conversations(count)
    return {"content": content}


@app.get("/api/conversations/history")
async def get_history(session_id: str = None, date: str = None):
    """
    Load conversation history for display in UI.

    Either provide session_id for a specific session,
    or date (YYYY-MM-DD) for all conversations from that day.
    """
    if not session_id and not date:
        return {"error": "Provide either session_id or date parameter"}

    data = get_conversation_data(session_id=session_id, date=date)
    return data


# ============== Server-Sent Events ==============

def get_tasks_for_panel() -> list:
    """Get tasks for the task panel."""
    from ..tools.worker.task import get_tasks_data
    # Don't filter by status - return all tasks so SSE updates include completed ones
    return get_tasks_data(limit=100)


@app.get("/api/events")
async def sse_endpoint():
    """
    Server-Sent Events endpoint for real-time updates.

    Event types:
    - init: Initial state on connection
    - tasks_update: Task list updated
    - projects_update: Project list updated
    """
    async def event_generator():
        queue = sse_manager.subscribe()
        try:
            # Send initial state
            tasks = get_tasks_for_panel()
            projects = get_projects_data(status="active")
            init_data = {
                "tasks": tasks,
                "projects": projects,
                "timestamp": datetime.now().isoformat()
            }
            yield {
                "event": "init",
                "data": json.dumps(init_data)
            }

            # Stream events from queue
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": message["event"],
                        "data": json.dumps(message["data"])
                    }
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.unsubscribe(queue)

    return EventSourceResponse(event_generator())


# ============== Projects ==============

from ..tools.worker.project import (
    create_project, get_projects, get_projects_data, get_project, update_project,
    add_milestone, archive_project, delete_project, get_projects_with_deadlines,
    get_project_notes, get_project_notes_count, prepend_project_note
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


class ProjectArchiveRequest(BaseModel):
    reason: str = ""
    outcome: str = "completed"  # completed, abandoned, paused, superseded


class ProjectNoteRequest(BaseModel):
    title: str
    content: str
    note_type: str = "note"  # note, research, update, decision


@app.get("/api/projects")
async def list_projects(status: str = "active", project_type: Optional[str] = None):
    """Get projects."""
    projects = get_projects_data(status=status, project_type=project_type)
    return {"projects": projects}


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
async def archive_project_endpoint(project_id: str, request: ProjectArchiveRequest = None):
    """Archive a project with behavioral context."""
    if request:
        result = archive_project(project_id, reason=request.reason, outcome=request.outcome)
    else:
        result = archive_project(project_id)
    return {"status": "success", "message": result}


@app.get("/api/projects/{project_id}/notes")
async def get_project_notes_endpoint(project_id: str):
    """Get project notes."""
    notes = get_project_notes(project_id)
    count = get_project_notes_count(project_id)
    return {"project_id": project_id, "notes": notes, "count": count}


@app.post("/api/projects/{project_id}/notes")
async def add_project_note_endpoint(project_id: str, request: ProjectNoteRequest):
    """Add a note to a project."""
    result = prepend_project_note(
        project_id=project_id,
        title=request.title,
        content=request.content,
        note_type=request.note_type
    )
    return {"status": "success", "message": result}


@app.post("/api/projects/{project_id}/complete")
async def complete_project_endpoint(project_id: str):
    """Mark a project as completed."""
    result = update_project(project_id, status="completed")
    return {"status": "success", "message": result}


@app.delete("/api/projects/{project_id}")
async def delete_project_endpoint(project_id: str, delete_tasks: bool = True):
    """Delete a project and optionally its associated tasks."""
    result = delete_project(project_id, delete_tasks=delete_tasks)
    return {"status": "success", "message": result}


# ============== Tasks ==============

from ..tools.worker.task import (
    create_task, create_learning_task, get_tasks, get_tasks_data, get_task,
    get_daily_view, add_quick_task, update_task_status, delete_task,
    get_recent_results, get_result, get_completed_tasks_data, archive_task
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


class TaskStatusRequest(BaseModel):
    status: str


class TaskArchiveRequest(BaseModel):
    reason: str = ""
    outcome: str = "abandoned"  # completed, abandoned, deferred, superseded


@app.get("/api/tasks")
async def list_tasks(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    exclude_snoozed: bool = True
):
    """Get tasks with optional filters."""
    tasks = get_tasks_data(
        status=status,
        project_id=project_id,
        priority=priority,
        limit=limit,
        exclude_snoozed=exclude_snoozed
    )
    return {"tasks": tasks}


@app.get("/api/tasks/daily")
async def get_todays_tasks(date: Optional[str] = None):
    """Get daily task view."""
    content = get_daily_view(date)
    return {"content": content}


@app.get("/api/tasks/completed")
async def get_completed_tasks(days: int = 30, limit: int = 50):
    """Get recently completed tasks."""
    tasks = get_completed_tasks_data(days=days, limit=limit)
    return {"tasks": tasks}


@app.get("/api/tasks/{task_id}")
async def get_task_details(task_id: str):
    """Get task details."""
    from ..tools.worker.task import get_task as get_task_detail
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
async def update_task_status_endpoint(task_id: str, request: TaskStatusRequest):
    """Update task status."""
    result = update_task_status(task_id, request.status)
    return {"status": "success", "message": result}


@app.delete("/api/tasks/{task_id}")
async def delete_task_endpoint(task_id: str):
    """Delete a task."""
    result = delete_task(task_id)
    return {"status": "success", "message": result}


@app.post("/api/tasks/{task_id}/archive")
async def archive_task_endpoint(task_id: str, request: TaskArchiveRequest = None):
    """Archive a task with behavioral context."""
    if request:
        result = archive_task(task_id, reason=request.reason, outcome=request.outcome)
    else:
        result = archive_task(task_id)
    return {"status": "success", "message": result}


class TaskSnoozeRequest(BaseModel):
    until_date: Optional[str] = None  # ISO format YYYY-MM-DD, default: tomorrow


@app.post("/api/tasks/{task_id}/snooze")
async def snooze_task_endpoint(task_id: str, request: TaskSnoozeRequest = None):
    """Snooze a task until a specific date (default: tomorrow)."""
    from ..tools.worker.task import snooze_task
    until_date = request.until_date if request else None
    result = snooze_task(task_id, until_date)
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


# ============== File Upload ==============

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the inbox for processing by the Ingestion Agent.

    Streams file to disk in chunks to handle files of any size without
    loading them entirely into memory.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Ensure inbox directory exists
    INBOX_PENDING_DIR.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    filename = Path(file.filename).name
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)

    # Handle duplicate filenames by appending timestamp
    file_path = INBOX_PENDING_DIR / filename
    if file_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        stem = file_path.stem
        suffix = file_path.suffix
        filename = f"{stem}_{timestamp}{suffix}"
        file_path = INBOX_PENDING_DIR / filename

    # Stream to disk in chunks (64KB)
    CHUNK_SIZE = 64 * 1024
    total_bytes = 0

    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while chunk := await file.read(CHUNK_SIZE):
                await out_file.write(chunk)
                total_bytes += len(chunk)

        return {
            "status": "success",
            "filename": filename,
            "size": total_bytes,
            "message": f"File '{filename}' uploaded successfully. It will be processed by the Archivist shortly."
        }
    except Exception as e:
        # Clean up on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


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
