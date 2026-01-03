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


@tool("send_notification", "Send a notification to the user")
def send_notification(title: str, message: str, priority: str = "normal") -> dict:
    """Send a notification to the user.

    For now, this just logs the notification. In the future it could
    integrate with system notifications, email, etc.

    Args:
        title: Notification title
        message: Notification body
        priority: "low", "normal", or "high"
    """
    _ensure_system_dir()

    # Log notification to a file
    notifications_path = SYSTEM_DIR / "notifications.jsonl"

    from datetime import datetime
    notification = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "title": title,
        "message": message,
        "priority": priority,
        "read": False
    }

    with open(notifications_path, "a") as f:
        f.write(json.dumps(notification) + "\n")

    return {"status": "sent", "title": title}


@tool("get_notifications", "Get recent notifications")
def get_notifications(unread_only: bool = False) -> list:
    """Get recent notifications."""
    _ensure_system_dir()

    notifications_path = SYSTEM_DIR / "notifications.jsonl"
    if not notifications_path.exists():
        return []

    notifications = []
    with open(notifications_path) as f:
        for line in f:
            if line.strip():
                n = json.loads(line)
                if unread_only and n.get("read"):
                    continue
                notifications.append(n)

    # Return most recent first
    notifications.reverse()
    return notifications[:50]  # Limit to 50


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


@tool(
    "send_notifications_batch",
    "Send multiple notifications in a single operation. More efficient than multiple send_notification calls.",
    input_schema={
        "type": "object",
        "properties": {
            "notifications": {
                "type": "array",
                "description": "List of notifications to send",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Notification title (required)"},
                        "message": {"type": "string", "description": "Notification body (required)"},
                        "priority": {"type": "string", "enum": ["low", "normal", "high"], "description": "Priority level"}
                    },
                    "required": ["title", "message"]
                }
            }
        },
        "required": ["notifications"]
    }
)
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
