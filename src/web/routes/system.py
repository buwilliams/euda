"""
System API Routes - Health, about, settings, events
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...llms import get_client, get_model, get_provider, get_providers_config, invalidate_client
from ...llms.base import _load_config, CONFIG_PATH, VALID_PROVIDERS
from ...tools.data.jobs import list_jobs
from ...tools.data.profile import get_profile


router = APIRouter()

DOCS_DIR = Path(__file__).parent.parent.parent.parent / "docs"
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
QUOTES_FILE = DATA_DIR / "system" / "quotes.json"


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
