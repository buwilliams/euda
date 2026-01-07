"""
System Tools - System configuration and notifications.
"""

import json
import threading
from pathlib import Path
from typing import Optional

from . import tool


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


DATA_DIR = Path(__file__).parent.parent.parent / "data"
SYSTEM_DIR = DATA_DIR / "system"


def _ensure_system_dir():
    """Ensure system directory exists."""
    SYSTEM_DIR.mkdir(parents=True, exist_ok=True)


@tool("get_system_config", "Get system configuration")
def get_system_config() -> dict:
    """Get system configuration."""
    _ensure_system_dir()

    config_path = SYSTEM_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


@tool("update_system_config", "Update system configuration")
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


@tool("done_working", "Signal that you have finished your current work cycle and are ready to sleep")
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


