"""
System Tools - System configuration and notifications.
"""

import json
import threading
from pathlib import Path
from typing import Optional

from .. import tool


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


@tool("get_system_config", "Get system configuration settings. Use when: checking system settings or LLM config.", tool_type="system")
def get_system_config() -> dict:
    """Get system configuration."""
    _ensure_system_dir()

    config_path = SYSTEM_DIR / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


@tool("update_system_config", "Update system configuration settings. Use when: changing system behavior or settings.", tool_type="system")
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


@tool("done_working", "Signal that you have finished your current work cycle. Use when: all assigned work is complete, no more actions needed, or blocked.", tool_type="system")
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


@tool(
    "send_notifications_batch",
    "Send multiple notifications in a single operation. Use when: sending multiple alerts to the user at once.",
    input_schema={
        "type": "object",
        "properties": {
            "notifications": {
                "type": "array",
                "description": "List of notifications to send",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Notification title/agent name (required)"},
                        "message": {"type": "string", "description": "Notification body (required)"},
                        "priority": {"type": "string", "enum": ["low", "normal", "high"], "description": "Priority level"}
                    },
                    "required": ["title", "message"]
                }
            }
        },
        "required": ["notifications"]
    },
    tool_type="system"
)
def send_notifications_batch(notifications: list) -> dict:
    """Send multiple notifications in a single operation.

    Returns:
        Dict with 'sent' (list of results) and 'count'
    """
    from .notifications import send_chat_message

    results = []

    for notif in notifications:
        result = send_chat_message(
            message=notif["message"],
            agent_name=notif.get("title", "Euno")
        )
        results.append(result)

    return {
        "sent": results,
        "count": len(results)
    }


@tool("schedule_reminder", "Schedule a reminder to be sent at a specific future time. Use when: user asks to be reminded about something at a certain time.", tool_type="system")
def schedule_reminder(message: str, scheduled_at: str) -> dict:
    """Schedule a reminder to be sent at a specific time.

    The reminder will be delivered as a notification when the scheduled time arrives.
    This is a zero-cost operation - the Python scheduler handles delivery without LLM calls.
    The reminder appears in the Focus tab until delivered.

    Args:
        message: The reminder message to send to the user
        scheduled_at: ISO datetime string for when to send (e.g., "2026-01-15T15:00:00")

    Returns:
        Dict with scheduled status, job_id, and scheduled_at time
    """
    from ..data.jobs import create_job

    # Extract date portion from scheduled_at for due_date (YYYY-MM-DD)
    due_date = scheduled_at.split("T")[0] if "T" in scheduled_at else scheduled_at[:10]

    # Create reminder as a top-level job (no parent) so it appears in Focus tab
    job = create_job(
        name=f"Reminder: {message[:50]}{'...' if len(message) > 50 else ''}",
        description=message,
        parent_id=None,  # Top-level job, visible in Focus tab
        tags=["scheduled", "reminder"],
        scheduled_at=scheduled_at,
        due_date=due_date,  # Shows in Today/Upcoming based on scheduled date
        created_by="agent"
    )

    return {
        "scheduled": True,
        "job_id": job["id"],
        "scheduled_at": scheduled_at,
        "message": f"Reminder scheduled for {scheduled_at}"
    }

