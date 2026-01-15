"""
System API Routes - Health, about, settings, events
"""

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...llms import get_client, get_model, get_provider, get_providers_config, invalidate_client
from ...llms.base import _load_config, CONFIG_PATH, VALID_PROVIDERS
from ...tools.data.jobs import list_jobs, _get_connection
from ...tools.data.profile import get_profile


router = APIRouter()

DOCS_DIR = Path(__file__).parent.parent.parent.parent / "docs"
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
QUOTES_FILE = DATA_DIR / "system" / "quotes.json"


class FreshStartRequest(BaseModel):
    confirm: str  # Must be "yes" to proceed


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

def _load_quotes_state() -> dict:
    """Load quotes state from disk."""
    if QUOTES_FILE.exists():
        try:
            with open(QUOTES_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"current": None, "date": None, "history": []}


def _save_quotes_state(state: dict):
    """Save quotes state to disk."""
    QUOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUOTES_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _generate_quote(profile_content: str, history: list) -> dict:
    """Generate a personalized quote using the configured LLM."""
    client = get_client()

    # Build context about recently used quotes to avoid
    history_context = ""
    if history:
        recent = history[-50:]  # Show last 50 to avoid repetition
        history_context = "\n\nQuotes to AVOID (recently used):\n"
        for q in recent:
            history_context += f"- \"{q['quote']}\" — {q['author']}\n"

    prompt = f"""Based on this user's profile, select or compose an inspiring quote that would resonate with them today.

User Profile:
{profile_content if profile_content else "No profile available - provide a generally inspiring quote."}
{history_context}

Respond with ONLY a JSON object in this exact format (no markdown, no explanation):
{{"quote": "The quote text here", "author": "Author Name"}}

The quote can be from a famous person, philosopher, writer, or you can compose an original one attributed to "Unknown" or "Ancient Wisdom". Make it meaningful and relevant to the user's interests, goals, or values."""

    response = client.create(
        max_tokens=256,
        system="You are a helpful assistant that provides inspiring quotes.",
        messages=[{"role": "user", "content": prompt}],
        agent_id="system"
    )

    text = response.content[0].text.strip()

    # Parse JSON response
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback if parsing fails
        return {
            "quote": "The journey of a thousand miles begins with a single step.",
            "author": "Lao Tzu"
        }


@router.get("/daily-quote")
def daily_quote():
    """Get a personalized daily quote."""
    today = datetime.now().strftime("%Y-%m-%d")
    state = _load_quotes_state()

    # Return cached quote if already generated today
    if state.get("date") == today and state.get("current"):
        return state["current"]

    # Get user profile for personalization
    profile = get_profile("user")
    profile_content = profile.get("content", "") if profile.get("exists") else ""

    # Get history (last 365 quotes)
    history = state.get("history", [])[-365:]

    # Generate new quote
    quote = _generate_quote(profile_content, history)

    # Update state
    history.append(quote)
    state = {
        "current": quote,
        "date": today,
        "history": history[-365:]  # Keep only last 365
    }
    _save_quotes_state(state)

    return quote


# ============== Costs ==============

@router.get("/costs")
def get_costs():
    """Get cost summary for session, today, 7 days, and this month."""
    from ...cost_tracker import get_cost_summary
    return get_cost_summary()


@router.get("/costs/by-agent")
def get_costs_by_agent(days: int = 30):
    """Get cost breakdown by agent for the specified number of days."""
    from ...cost_tracker import get_costs_by_agent
    return get_costs_by_agent(days)


# ============== Settings ==============

@router.get("/settings")
def get_settings():
    """Get current LLM settings with all providers and speech capabilities."""
    from ...speech import supports_stt, supports_tts

    config = _load_config()
    current_provider = get_provider()
    return {
        "llm": {
            "provider": current_provider,
            "model": get_model(),
            "providers": get_providers_config(),
            "budget_limit": config.get("llm", {}).get("budget_limit")
        },
        "speech": {
            "stt_available": supports_stt(current_provider),
            "tts_available": supports_tts(current_provider),
        },
        "schedules": config.get("schedules", {})
    }


@router.put("/settings/llm")
def update_llm_settings(data: dict):
    """Update LLM settings (provider, models, budget_limit)."""
    config = _load_config()

    # Update provider if specified
    if "default_provider" in data:
        provider = data["default_provider"]
        if provider in VALID_PROVIDERS:
            config["llm"]["provider"] = provider

    # Update models if specified
    if "providers" in data:
        for provider_id, settings in data["providers"].items():
            if provider_id in VALID_PROVIDERS and "model" in settings:
                config["llm"]["providers"][provider_id]["model"] = settings["model"]

    # Update budget limit if specified
    if "budget_limit" in data:
        config["llm"]["budget_limit"] = data["budget_limit"]

    # Save config
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    # Invalidate cached clients so next request uses new provider
    invalidate_client()

    # Also invalidate speech client since it depends on provider
    from ...speech import invalidate_speech_client
    invalidate_speech_client()

    return {"success": True, "llm": config["llm"]}


@router.put("/settings/schedules")
def update_schedules(data: dict):
    """Update schedule times."""
    config = _load_config()

    # Ensure schedules exists
    if "schedules" not in config:
        config["schedules"] = {}

    # Update each schedule provided
    for name, time in data.items():
        if name in config["schedules"]:
            config["schedules"][name] = time

    # Save config
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    return {"success": True, "schedules": config["schedules"]}


# ============== Fresh Start & Backups ==============

BACKUP_PREFIX = "data_backup-"


def _list_backups() -> List[dict]:
    """List all available backups sorted by date (newest first)."""
    project_dir = DATA_DIR.parent
    backups = []

    for item in project_dir.iterdir():
        if item.is_dir() and item.name.startswith(BACKUP_PREFIX):
            # Parse timestamp from name: data_backup-YYYYMMDD-HHMMSS
            timestamp_str = item.name[len(BACKUP_PREFIX):]
            try:
                # Get actual modification time as fallback
                mtime = item.stat().st_mtime
                backups.append({
                    "name": item.name,
                    "timestamp": timestamp_str,
                    "path": str(item),
                    "mtime": mtime
                })
            except OSError:
                continue

    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x["mtime"], reverse=True)
    return backups


def _perform_fresh_start() -> dict:
    """
    Reset all user data for a clean slate.

    Instead of deleting, moves the data directory to a timestamped backup,
    then creates a fresh data directory preserving only agent configs and profiles.

    Returns dict with backup_name and preserved items.
    """
    project_dir = DATA_DIR.parent
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_name = f"{BACKUP_PREFIX}{timestamp}"
    backup_path = project_dir / backup_name

    # Collect agent configs and profiles to preserve
    preserved = []
    agents_to_preserve = {}

    agents_dir = DATA_DIR / "agents"
    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                agent_id = agent_dir.name
                agents_to_preserve[agent_id] = {}

                # Preserve config.json
                config_file = agent_dir / "config.json"
                if config_file.exists():
                    agents_to_preserve[agent_id]["config"] = config_file.read_text()
                    preserved.append(f"agents/{agent_id}/config.json")

                # Preserve profile.md
                profile_file = agent_dir / "profile.md"
                if profile_file.exists():
                    agents_to_preserve[agent_id]["profile"] = profile_file.read_text()
                    preserved.append(f"agents/{agent_id}/profile.md")

    # Preserve system config
    system_config = None
    system_config_file = DATA_DIR / "system" / "config.json"
    if system_config_file.exists():
        system_config = system_config_file.read_text()
        preserved.append("system/config.json")

    # Close any open database connections
    try:
        from ...tools.data.jobs import _connection_pool
        for conn in _connection_pool.values():
            conn.close()
        _connection_pool.clear()
    except Exception:
        pass

    # Move data to backup
    if DATA_DIR.exists():
        shutil.move(str(DATA_DIR), str(backup_path))

    # Create fresh data directory structure
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Restore agents directory with only configs and profiles
    if agents_to_preserve:
        agents_dir = DATA_DIR / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        for agent_id, files in agents_to_preserve.items():
            agent_dir = agents_dir / agent_id
            agent_dir.mkdir(parents=True, exist_ok=True)

            if "config" in files:
                (agent_dir / "config.json").write_text(files["config"])
            if "profile" in files:
                (agent_dir / "profile.md").write_text(files["profile"])

    # Restore system config
    if system_config:
        system_dir = DATA_DIR / "system"
        system_dir.mkdir(parents=True, exist_ok=True)
        (system_dir / "config.json").write_text(system_config)

    # Create jobs directory
    (DATA_DIR / "jobs").mkdir(parents=True, exist_ok=True)

    return {
        "backup_name": backup_name,
        "preserved": preserved
    }


def _restore_backup(backup_name: str) -> dict:
    """
    Restore from a backup by swapping directories.

    The current data becomes a new backup, and the selected backup becomes data.
    """
    project_dir = DATA_DIR.parent
    backup_path = project_dir / backup_name

    if not backup_path.exists():
        return {"error": f"Backup not found: {backup_name}"}

    if not backup_path.is_dir():
        return {"error": f"Invalid backup: {backup_name}"}

    # Close any open database connections
    try:
        from ...tools.data.jobs import _connection_pool
        for conn in _connection_pool.values():
            conn.close()
        _connection_pool.clear()
    except Exception:
        pass

    # Create a backup of current data before restoring
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    current_backup_name = f"{BACKUP_PREFIX}{timestamp}"
    current_backup_path = project_dir / current_backup_name

    # Move current data to backup
    if DATA_DIR.exists():
        shutil.move(str(DATA_DIR), str(current_backup_path))

    # Restore selected backup as data
    shutil.move(str(backup_path), str(DATA_DIR))

    return {
        "restored_from": backup_name,
        "current_backed_up_as": current_backup_name
    }


def _delete_backup(backup_name: str) -> dict:
    """Delete a backup permanently."""
    project_dir = DATA_DIR.parent
    backup_path = project_dir / backup_name

    if not backup_path.exists():
        return {"error": f"Backup not found: {backup_name}"}

    if not backup_name.startswith(BACKUP_PREFIX):
        return {"error": "Invalid backup name"}

    shutil.rmtree(backup_path)
    return {"deleted": backup_name}


@router.post("/fresh-start")
def fresh_start():
    """
    Reset all user data for a clean slate.

    Moves current data to a timestamped backup and creates a fresh data directory.
    Agent configs and profiles are preserved. Use /api/backups to restore if needed.
    """
    result = _perform_fresh_start()

    return {
        "success": True,
        "backup_name": result["backup_name"],
        "preserved": result["preserved"],
        "message": f"Fresh start complete. Previous data backed up as {result['backup_name']}."
    }


@router.get("/backups")
def list_backups():
    """List all available backups."""
    backups = _list_backups()
    return {
        "backups": backups,
        "count": len(backups)
    }


class RestoreBackupRequest(BaseModel):
    backup_name: str


@router.post("/backups/restore")
def restore_backup(request: RestoreBackupRequest):
    """
    Restore from a backup.

    Current data is backed up first, then the selected backup becomes the active data.
    """
    result = _restore_backup(request.backup_name)

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {
        "success": True,
        "restored_from": result["restored_from"],
        "current_backed_up_as": result["current_backed_up_as"],
        "message": f"Restored from {result['restored_from']}. Previous data backed up as {result['current_backed_up_as']}."
    }


@router.delete("/backups/{backup_name}")
def delete_backup(backup_name: str):
    """Delete a backup permanently."""
    result = _delete_backup(backup_name)

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {
        "success": True,
        "deleted": result["deleted"],
        "message": f"Backup {result['deleted']} deleted permanently."
    }


# ============== SSE Events ==============

async def event_generator():
    """Generate SSE events for real-time updates."""
    from ...events import subscribe_ui, unsubscribe_ui

    # Send initial state
    all_jobs = list_jobs()
    yield f"event: init\ndata: {json.dumps({'jobs': all_jobs})}\n\n"

    # Subscribe to UI events (returns queue and shutdown event)
    event_queue, shutdown_event = subscribe_ui()

    try:
        while True:
            # Wait for either: queue event, shutdown signal, or timeout
            queue_task = asyncio.create_task(event_queue.get())
            shutdown_task = asyncio.create_task(shutdown_event.wait())

            done, pending = await asyncio.wait(
                [queue_task, shutdown_task],
                timeout=30,
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel any pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Check if shutdown was signaled
            if shutdown_task in done:
                break

            # Check if we got an event from the queue
            if queue_task in done:
                event = queue_task.result()
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
            else:
                # Timeout - send ping to keep connection alive
                yield f"event: ping\ndata: {{}}\n\n"
    finally:
        unsubscribe_ui(event_queue, shutdown_event)


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
