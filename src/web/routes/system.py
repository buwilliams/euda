"""
System API Routes - Health, about, settings, events
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...llms import get_client, get_model, get_provider, get_providers_config, invalidate_client
from ...llms.base import _load_config, LLM_CONFIG_PATH, VALID_PROVIDERS
from ...tools.data.jobs import list_jobs
from ...tools.data.identity import get_identity
from ...tools.system.fresh_start import (
    perform_fresh_start,
    list_backups as _list_backups,
    restore_backup as _restore_backup,
    delete_backup as _delete_backup,
)
from ...agent.cognition.metacognition import get_incident_tracker


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


def _generate_quote(identity_content: str, history: list) -> dict:
    """Generate a personalized quote using the configured LLM."""
    client = get_client()

    # Build context about recently used quotes to avoid
    history_context = ""
    if history:
        recent = history[-50:]  # Show last 50 to avoid repetition
        history_context = "\n\nQuotes to AVOID (recently used):\n"
        for q in recent:
            history_context += f"- \"{q['quote']}\" — {q['author']}\n"

    prompt = f"""Based on this user's identity, select or compose an inspiring quote that would resonate with them today.

User Identity:
{identity_content if identity_content else "No identity available - provide a generally inspiring quote."}
{history_context}

Respond with ONLY a JSON object in this exact format (no markdown, no explanation):
{{"quote": "The quote text here", "author": "Author Name"}}

The quote can be from a famous person, philosopher, writer, or you can compose an original one attributed to "Unknown" or "Ancient Wisdom". Make it meaningful and relevant to the user's interests, goals, concerns, or values."""

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

    # Get user identity for personalization
    identity = get_identity("user")
    identity_content = identity.get("content", "") if identity.get("exists") else ""

    # Get history (last 365 quotes)
    history = state.get("history", [])[-365:]

    # Generate new quote
    quote = _generate_quote(identity_content, history)

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
    from ...agent.cognition.metacognition import get_cost_summary
    return get_cost_summary()


@router.get("/costs/by-agent")
def get_costs_by_agent(days: int = 30):
    """Get cost breakdown by agent for the specified number of days."""
    from ...agent.cognition.metacognition import get_costs_by_agent
    return get_costs_by_agent(days)


# ============== Settings ==============

@router.get("/settings")
def get_settings():
    """Get current LLM settings with all providers and speech capabilities."""
    from ...tools.speech import supports_stt, supports_tts
    import json

    # Load LLM config
    llm_config = _load_config()
    current_provider = get_provider()
    budget_config = llm_config.get("budget", {})

    # Load system config for schedules
    system_config_path = DATA_DIR / "system" / "config.json"
    try:
        with open(system_config_path) as f:
            system_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        system_config = {}

    return {
        "llm": {
            "provider": current_provider,
            "model": get_model(),
            "providers": get_providers_config(),
            "budget": {
                "limit": budget_config.get("limit"),
                "period": budget_config.get("period", "monthly")
            }
        },
        "speech": {
            "stt_available": supports_stt(current_provider),
            "tts_available": supports_tts(current_provider),
        },
        "schedules": system_config.get("schedules", {})
    }


@router.put("/settings/llm")
def update_llm_settings(data: dict):
    """Update LLM settings (provider, model, budget)."""
    from ...agent.cognition.metacognition import get_token_awareness

    config = _load_config()

    # Update provider if specified
    if "default_provider" in data:
        provider = data["default_provider"]
        if provider in VALID_PROVIDERS:
            config["provider"] = provider

    # Update model if specified (new structure: single model at root level)
    if "model" in data:
        config["model"] = data["model"]

    # Update budget if specified (nested structure: budget.limit, budget.period)
    if "budget" in data:
        if "budget" not in config:
            config["budget"] = {}
        if "limit" in data["budget"]:
            config["budget"]["limit"] = data["budget"]["limit"]
        if "period" in data["budget"]:
            config["budget"]["period"] = data["budget"]["period"]

    # Save config to llm.json
    with open(LLM_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    # Invalidate cached clients so next request uses new provider
    invalidate_client()

    # Also invalidate speech client since it depends on provider
    from ...tools.speech import invalidate_speech_client
    invalidate_speech_client()

    # Invalidate token awareness cache so budget changes take effect
    get_token_awareness().invalidate_config()

    return {"success": True, "llm": {
        "provider": config["provider"],
        "model": config["model"],
        "budget": config.get("budget", {})
    }}


@router.put("/settings/schedules")
def update_schedules(data: dict):
    """Update schedule times."""
    # Load system config (not LLM config)
    system_config_path = DATA_DIR / "system" / "config.json"
    try:
        with open(system_config_path) as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}

    # Ensure schedules exists
    if "schedules" not in config:
        config["schedules"] = {}

    # Update each schedule provided
    for name, time in data.items():
        if name in config["schedules"]:
            config["schedules"][name] = time

    # Save config
    with open(system_config_path, "w") as f:
        json.dump(config, f, indent=2)

    return {"success": True, "schedules": config["schedules"]}


# ============== Fresh Start & Backups ==============

@router.post("/fresh-start")
def fresh_start():
    """
    Reset all user data for a clean slate.

    Creates a backup first, then resets user data while preserving
    agent configs, system config, and git-tracked files.
    """
    result = perform_fresh_start(create_backup_first=True)

    return {
        "success": True,
        "backup_name": result.get("backup_name"),
        "deleted": result.get("deleted", []),
        "reset": result.get("reset", []),
        "message": f"Fresh start complete. Previous data backed up as {result.get('backup_name')}."
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


# ============== Incidents ==============

@router.get("/incidents")
def list_incidents(agent_id: str = None, days: int = 7):
    """List incidents (unacknowledged and recent history).

    Args:
        agent_id: Optional filter by agent ID
        days: Number of days of history to include (default 7)

    Returns unacknowledged incidents and recent history.
    """
    tracker = get_incident_tracker()

    # Get unacknowledged incidents
    unacknowledged = tracker.get_unacknowledged(agent_id)

    # Get history
    history = tracker.get_history(days=days, agent_id=agent_id)

    return {
        "unacknowledged": [
            {
                "id": i.id,
                "agent_id": i.agent_id,
                "incident_type": i.incident_type,
                "severity": i.severity,
                "reason": i.reason,
                "details": i.details,
                "timestamp": i.timestamp
            }
            for i in unacknowledged
        ],
        "history": history,
        "unacknowledged_count": len(unacknowledged)
    }


@router.post("/incidents/{incident_id}/acknowledge")
def acknowledge_incident(incident_id: str):
    """Acknowledge an incident.

    Marks the incident as acknowledged, removing it from the unacknowledged list.
    """
    tracker = get_incident_tracker()
    success = tracker.acknowledge(incident_id, acknowledged_by="api")

    if not success:
        return {"success": False, "error": "Incident not found or already acknowledged"}

    return {
        "success": True,
        "incident_id": incident_id,
        "message": "Incident acknowledged"
    }


@router.post("/incidents/acknowledge-all")
def acknowledge_all_incidents(agent_id: str = None):
    """Acknowledge all incidents for an agent (or all agents).

    Args:
        agent_id: Optional agent ID filter. If not provided, acknowledges all incidents.
    """
    tracker = get_incident_tracker()
    count = tracker.acknowledge_all(agent_id, acknowledged_by="api")

    return {
        "success": True,
        "acknowledged_count": count,
        "agent_id": agent_id,
        "message": f"Acknowledged {count} incident(s)"
    }


# ============== SSE Events ==============

async def event_generator():
    """Generate SSE events for real-time updates."""
    from ..events import subscribe_ui, unsubscribe_ui

    # Send initial state
    all_jobs = list_jobs()
    yield f"event: init\ndata: {json.dumps({'jobs': all_jobs})}\n\n"

    # Subscribe to UI events (returns queue and shutdown event)
    event_queue, shutdown_event = subscribe_ui()

    # Track current tasks so we can cancel them on disconnect
    current_tasks = []

    try:
        while True:
            # Wait for either: queue event, shutdown signal, or timeout
            queue_task = asyncio.create_task(event_queue.get())
            shutdown_task = asyncio.create_task(shutdown_event.wait())
            current_tasks = [queue_task, shutdown_task]

            done, pending = await asyncio.wait(
                current_tasks,
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

            # Clear task references after handling
            current_tasks = []

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
    except asyncio.CancelledError:
        # Client disconnected - clean up gracefully
        pass
    finally:
        # Cancel any still-running tasks to prevent "Task was destroyed" warnings
        for task in current_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
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
