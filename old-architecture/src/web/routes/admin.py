"""
Admin routes for Euno web API: settings, health, agent status, upload, about.
"""

import re
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ...tools.worker.task import get_tasks_data
from ...tools.worker.project import get_projects_data


router = APIRouter(tags=["admin"])

BASE_DIR = Path(__file__).parent.parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
INBOX_PENDING_DIR = BASE_DIR / "data" / "archivist" / "state" / "inbox" / "pending"


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


# ============== Background Task Helpers ==============

def get_tasks_for_panel() -> list:
    """Get tasks for the task panel."""
    return get_tasks_data(limit=100)


async def watch_tasks():
    """Watch tasks queue and broadcast changes via SSE."""
    from watchfiles import awatch
    tasks_dir = BASE_DIR / "data" / "worker" / "state" / "tasks"
    queue_file = tasks_dir / "queue.json"

    if not tasks_dir.exists():
        tasks_dir.mkdir(parents=True, exist_ok=True)

    last_mtime = None

    async for changes in awatch(tasks_dir):
        if queue_file.exists():
            current_mtime = queue_file.stat().st_mtime
            if current_mtime != last_mtime:
                last_mtime = current_mtime
                tasks = get_tasks_for_panel()
                await sse_manager.broadcast("tasks_update", {"tasks": tasks})


async def watch_projects():
    """Watch projects directory and broadcast changes via SSE."""
    from watchfiles import awatch
    projects_dir = BASE_DIR / "data" / "worker" / "state" / "projects"

    if not projects_dir.exists():
        projects_dir.mkdir(parents=True, exist_ok=True)

    async for changes in awatch(projects_dir):
        projects = get_projects_data(status="active")
        await sse_manager.broadcast("projects_update", {"projects": projects})


# ============== Request Models ==============

class LLMSettingsRequest(BaseModel):
    default_provider: str
    providers: Optional[dict] = None


# ============== Agent Info ==============

AGENT_INFO = {
    "archivist": {"display_name": "Archivist", "description": "Transforms data into log entries"},
    "profiler": {"display_name": "Profiler", "description": "Synthesizes user profile from patterns"},
    "curator": {"display_name": "Curator", "description": "Surface the right thing at the right time"},
    "friend": {"display_name": "Friend", "description": "User-facing conversations"},
    "worker": {"display_name": "Worker", "description": "Execute approved tasks"},
    "adaptor": {"display_name": "Adaptor", "description": "Evolves agent identities based on profile"},
}


def get_agent_state(agent_name: str) -> dict:
    """Load agent state from file if it exists."""
    state_file = BASE_DIR / "data" / agent_name / "state" / "state.json"
    if state_file.exists():
        with open(state_file, 'r') as f:
            return json.load(f)
    return {}


# ============== Root & Static ==============

@router.get("/")
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


@router.get("/app")
async def app_page():
    """Serve the main app page."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="App not found. Run from project root.")


# ============== Settings ==============

@router.get("/api/settings")
async def get_settings():
    """Get application settings."""
    from ...providers import load_config, CONFIG_FILE

    llm_config = load_config()
    return {
        "llm": llm_config,
        "config_path": str(CONFIG_FILE)
    }


@router.put("/api/settings/llm")
async def update_llm_settings(request: LLMSettingsRequest):
    """Update LLM settings."""
    from ...providers import load_config, reload_config, CONFIG_FILE

    config = load_config()

    if request.default_provider not in config.get("providers", {}):
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.default_provider}")

    config["default_provider"] = request.default_provider

    if request.providers:
        for provider_name, provider_settings in request.providers.items():
            if provider_name in config["providers"]:
                config["providers"][provider_name].update(provider_settings)

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

    reload_config()
    return {"success": True, "message": "LLM settings updated"}


# ============== Agent Status ==============

@router.get("/api/agents/status")
async def get_agent_status():
    """Get status of all agents with real state data."""
    from .chat import sessions  # Import sessions from chat module

    agents = []

    for agent_name, info in AGENT_INFO.items():
        state = get_agent_state(agent_name)

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

        if state.get("updated"):
            agent_data["last_active"] = state["updated"]

        if agent_name == "friend":
            agent_data["active_sessions"] = len(sessions)

        if agent_name == "archivist":
            pending_dir = BASE_DIR / "data" / "archivist" / "state" / "inbox" / "pending"
            if pending_dir.exists():
                pending_count = len([f for f in pending_dir.iterdir() if f.is_file() and not f.name.startswith('.')])
                agent_data["pending_files"] = pending_count
                if pending_count > 0:
                    agent_data["status"] = "working"
            if state.get("current_file"):
                agent_data["current_file"] = state["current_file"]

        if state.get("last_work_time"):
            agent_data["last_work"] = state["last_work_time"]

        if state.get("work_count"):
            agent_data["work_count"] = state["work_count"]

        agents.append(agent_data)

    return {
        "agents": agents,
        "timestamp": datetime.now().isoformat()
    }


# ============== Server-Sent Events ==============

@router.get("/api/events")
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

            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": message["event"],
                        "data": json.dumps(message["data"])
                    }
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.unsubscribe(queue)

    return EventSourceResponse(event_generator())


# ============== File Upload ==============

@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the inbox for processing by the Archivist.

    Streams file to disk in chunks to handle files of any size.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    INBOX_PENDING_DIR.mkdir(parents=True, exist_ok=True)

    filename = Path(file.filename).name
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)

    file_path = INBOX_PENDING_DIR / filename
    if file_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        stem = file_path.stem
        suffix = file_path.suffix
        filename = f"{stem}_{timestamp}{suffix}"
        file_path = INBOX_PENDING_DIR / filename

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
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


# ============== About ==============

@router.get("/api/about")
async def get_about():
    """Get about page content from docs/1_pitch.md."""
    pitch_file = BASE_DIR / "docs" / "1_pitch.md"

    if not pitch_file.exists():
        return {"content": "# About\n\nContent not available."}

    content = pitch_file.read_text()
    return {"content": content}


# ============== Health ==============

@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Legacy endpoints for compatibility
@router.get("/health")
async def health_legacy():
    return await health_check()
