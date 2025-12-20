"""
Notification system for agent-to-user communication.

Allows agents to queue messages/prompts for the user that appear
in the activity feed and can trigger chat interactions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
NOTIFICATIONS_DIR = DATA_DIR / "notifications"
NOTIFICATIONS_DIR.mkdir(parents=True, exist_ok=True)


def queue_notification(
    agent_name: str,
    title: str,
    message: str,
    notification_type: str = "info",
    action_prompt: Optional[str] = None,
    priority: str = "normal",
    data: Optional[dict] = None
) -> str:
    """
    Queue a notification for the user.

    Args:
        agent_name: Which agent is sending this
        title: Short title for the activity feed (e.g., "Identity proposal ready")
        message: Longer message shown when expanded
        notification_type: Type of notification - "info", "approval", "question", "alert"
        action_prompt: Optional prompt to inject into chat when clicked
        priority: "low", "normal", "high"
        data: Optional structured data (e.g., filename for approval)

    Returns:
        Confirmation message
    """
    notification = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "agent_name": agent_name,
        "title": title,
        "message": message,
        "type": notification_type,
        "action_prompt": action_prompt,
        "priority": priority,
        "data": data or {},
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "seen": False
    }

    # Save notification
    filename = f"{notification['id']}.json"
    with open(NOTIFICATIONS_DIR / filename, 'w') as f:
        json.dump(notification, f, indent=2)

    return f"Notification queued: {title}"


def get_pending_notifications(include_seen: bool = False) -> list:
    """
    Get all pending notifications.

    Args:
        include_seen: Include notifications that have been seen but not dismissed

    Returns:
        List of notification dictionaries
    """
    notifications = []

    for f in sorted(NOTIFICATIONS_DIR.glob("*.json"), reverse=True):
        with open(f, 'r') as file:
            notification = json.load(file)

        if notification.get("status") != "pending":
            continue

        if not include_seen and notification.get("seen"):
            continue

        notification["filename"] = f.name
        notifications.append(notification)

    # Sort by priority then date
    priority_order = {"high": 0, "normal": 1, "low": 2}
    notifications.sort(key=lambda n: (
        priority_order.get(n.get("priority", "normal"), 1),
        n.get("created_at", "")
    ))

    return notifications


def mark_seen(notification_id: str) -> str:
    """Mark a notification as seen."""
    for f in NOTIFICATIONS_DIR.glob("*.json"):
        with open(f, 'r') as file:
            notification = json.load(file)

        if notification.get("id") == notification_id:
            notification["seen"] = True
            notification["seen_at"] = datetime.now().isoformat()
            with open(f, 'w') as file:
                json.dump(notification, file, indent=2)
            return "Marked as seen"

    return "Notification not found"


def dismiss_notification(notification_id: str) -> str:
    """Dismiss/complete a notification."""
    for f in NOTIFICATIONS_DIR.glob("*.json"):
        with open(f, 'r') as file:
            notification = json.load(file)

        if notification.get("id") == notification_id:
            notification["status"] = "dismissed"
            notification["dismissed_at"] = datetime.now().isoformat()
            with open(f, 'w') as file:
                json.dump(notification, file, indent=2)
            return "Notification dismissed"

    return "Notification not found"


def check_for_pending_approvals() -> list:
    """
    Check various approval queues and create notifications if needed.
    Called periodically to sync approval queues with notifications.
    """
    from .identity import get_pending_evolutions

    notifications_created = []

    # Check identity evolution proposals
    evolutions = get_pending_evolutions()
    if "No pending" not in evolutions:
        # Parse the pending evolutions and create notifications
        EVOLUTION_DIR = DATA_DIR / "agents" / "evolution"
        for f in EVOLUTION_DIR.glob("*.json"):
            with open(f, 'r') as file:
                proposal = json.load(file)

            if proposal.get("status") != "pending":
                continue

            # Check if notification already exists for this
            notification_exists = False
            for nf in NOTIFICATIONS_DIR.glob("*.json"):
                with open(nf, 'r') as nfile:
                    n = json.load(nfile)
                if (n.get("data", {}).get("proposal_file") == f.name and
                    n.get("status") == "pending"):
                    notification_exists = True
                    break

            if not notification_exists:
                agent = proposal.get("agent_name", "Unknown")
                queue_notification(
                    agent_name=agent,
                    title=f"{agent.title()} wants to evolve",
                    message=f"Identity evolution proposal: {proposal.get('rationale', '')[:100]}...",
                    notification_type="approval",
                    action_prompt=f"Let's review the identity evolution proposal from {agent}. What changes are you proposing?",
                    priority="normal",
                    data={"proposal_file": f.name, "type": "identity_evolution"}
                )
                notifications_created.append(f"Identity evolution: {agent}")

    return notifications_created


# Tool definitions for agents
NOTIFICATION_TOOLS = [
    {
        "name": "queue_notification",
        "description": "Send a notification to the user that will appear in their activity feed. Use this when you have something to tell the user proactively, need their input on something, or want to surface an approval request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Your agent name"
                },
                "title": {
                    "type": "string",
                    "description": "Short title for the notification (shown in activity feed)"
                },
                "message": {
                    "type": "string",
                    "description": "Longer message with details"
                },
                "notification_type": {
                    "type": "string",
                    "enum": ["info", "approval", "question", "alert"],
                    "description": "Type: info (FYI), approval (needs action), question (needs input), alert (important)"
                },
                "action_prompt": {
                    "type": "string",
                    "description": "Optional message to inject into chat when user clicks the notification"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high"],
                    "description": "Priority level"
                }
            },
            "required": ["agent_name", "title", "message"]
        }
    }
]

NOTIFICATION_HANDLERS = {
    "queue_notification": queue_notification,
}
