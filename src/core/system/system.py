"""
System Tools - System configuration and notifications.
"""

import json
import threading
from pathlib import Path
from typing import Optional



# Thread-local storage for agent context
_agent_context = threading.local()


def set_agent_context(agent):
    """Set the current agent context for this thread."""
    _agent_context.agent = agent


def get_agent_context():
    """Get the current agent context for this thread."""
    return getattr(_agent_context, 'agent', None)


def clear_agent_context():
    """Clear the agent context for this thread."""
    _agent_context.agent = None


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SYSTEM_DIR = DATA_DIR / "system"


def _ensure_system_dir():
    """Ensure system directory exists."""
    SYSTEM_DIR.mkdir(parents=True, exist_ok=True)


def get_system_config() -> dict:
    """Get system configuration."""
    _ensure_system_dir()

    config_path = SYSTEM_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def update_system_config(key: str, value: str) -> dict:
    """Update a system configuration value."""
    _ensure_system_dir()

    config_path = SYSTEM_DIR / "config.json"

    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

    config[key] = value

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return {"status": "updated", "key": key}


def done_working(summary: str = "") -> dict:
    """Signal that the agent has finished working and is ready to sleep.

    Call this when you have:
    - Completed all tasks you can work on
    - Determined there's nothing for you to do
    - Finished a significant piece of work and want to pause

    Args:
        summary: Brief summary of what was accomplished (optional)

    Returns:
        Confirmation that sleep mode will begin
    """
    agent = get_agent_context()
    if agent:
        agent._work_done = True
        agent._log("done_working", {"summary": summary} if summary else None)

    return {
        "status": "acknowledged",
        "message": "Work cycle complete. Going to sleep.",
        "summary": summary
    }


def send_notifications_batch(notifications: list) -> dict:
    """Send multiple notifications in a single operation.

    Returns:
        Dict with 'sent' (list of results) and 'count'
    """
    results = []

    for notif in notifications:
        result = send_notification(
            title=notif["title"],
            message=notif["message"],
            priority=notif.get("priority", "normal")
        )
        results.append(result)

    return {
        "sent": results,
        "count": len(results)
    }


def set_nested_config(key: str, value) -> dict:
    """Update a nested system configuration value using dot notation.

    Args:
        key: Dot-notation key (e.g., 'logging.level' or 'schedules.morning')
        value: Value to set (can be any JSON-serializable type)

    Returns:
        Status dict with key and previous value
    """
    _ensure_system_dir()

    config_path = SYSTEM_DIR / "config.json"

    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

    # Navigate to parent and set the value
    parts = key.split(".")
    current = config
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Store previous value for reporting
    previous = current.get(parts[-1])

    # Set the new value
    current[parts[-1]] = value

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return {"status": "updated", "key": key, "previous": previous}


def trigger_config_reload() -> dict:
    """Trigger reload of all cached configurations.

    Invalidates caches for:
    - Prompt templates
    - LLM client
    - Token awareness config

    Returns:
        Dict with list of invalidated caches
    """
    invalidated = []

    # Clear prompt template cache
    try:
        from src.agent.cognition.reasoning.prompts import clear_cache as clear_prompt_cache
        clear_prompt_cache()
        invalidated.append("prompt_templates")
    except ImportError:
        pass

    # Invalidate LLM client cache
    try:
        from src.llms import invalidate_client
        invalidate_client()
        invalidated.append("llm_client")
    except ImportError:
        pass

    # Invalidate token awareness config
    try:
        from src.agent.cognition.metacognition import get_token_awareness
        get_token_awareness().invalidate_config()
        invalidated.append("token_awareness")
    except ImportError:
        pass

    return {"invalidated": invalidated}

