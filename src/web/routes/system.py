"""
System API Routes - Health, about, settings, events
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...llms import get_client, get_model, get_provider, get_providers_config, PROVIDERS
from ...llms.base import _load_config, CONFIG_PATH
from ...tools.jobs import list_jobs
from ...tools.user import get_user_profile


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

    response = client.messages.create(
        model=get_model(),
        max_tokens=256,
        system="You are a helpful assistant that provides inspiring quotes.",
        messages=[{"role": "user", "content": prompt}]
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
    profile = get_user_profile()
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


# ============== Settings ==============

@router.get("/settings")
def get_settings():
    """Get current LLM settings with all providers."""
    return {
        "llm": {
            "provider": get_provider(),
            "model": get_model(),
            "providers": get_providers_config()
        }
    }


@router.put("/settings/llm")
def update_llm_settings(data: dict):
    """Update LLM settings (provider, models)."""
    config = _load_config()

    if "llm" not in config:
        config["llm"] = {}

    # Update provider if specified
    if "default_provider" in data:
        provider = data["default_provider"]
        if provider in PROVIDERS:
            config["llm"]["provider"] = provider

    # Update models if specified
    if "providers" in data:
        if "models" not in config["llm"]:
            config["llm"]["models"] = {}
        for provider_id, settings in data["providers"].items():
            if provider_id in PROVIDERS and "default_model" in settings:
                config["llm"]["models"][provider_id] = settings["default_model"]

    # Save config
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    return {"success": True, "llm": config["llm"]}


# ============== SSE Events ==============

async def event_generator():
    """Generate SSE events for real-time updates."""
    from ...events import subscribe_ui, unsubscribe_ui

    # Send initial state
    all_jobs = list_jobs()
    yield f"event: init\ndata: {json.dumps({'jobs': all_jobs})}\n\n"

    # Subscribe to UI events
    event_queue = subscribe_ui()

    try:
        while True:
            try:
                # Wait for events with timeout for ping
                event = await asyncio.wait_for(event_queue.get(), timeout=30)
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                yield f"event: ping\ndata: {{}}\n\n"
    finally:
        unsubscribe_ui(event_queue)


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
