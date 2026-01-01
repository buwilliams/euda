"""
System Tools - System configuration and notifications.
"""

import json
from pathlib import Path
from typing import Optional

from . import tool


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
