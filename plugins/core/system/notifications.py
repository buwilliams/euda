"""
Notification Tools - Send messages to the user via chat/SSE.

These tools allow agents to proactively communicate with users
when they have the app open.
"""

from datetime import datetime
from typing import Optional

from src.web.events import emit_ui_event, has_connected_clients


def send_chat_message(message: str, agent_name: str = "Curator") -> dict:
    """Send a message to the user's chat.

    The message will appear in the chat tab as if from an agent.
    Only works if the user has the app open (SSE connection active).

    Args:
        message: The message content to display
        agent_name: Who the message is from (for display purposes)

    Returns:
        Dict with delivered status and reason if not delivered
    """
    if not has_connected_clients():
        return {"delivered": False, "reason": "No connected clients"}

    emit_ui_event("agent_message", {
        "message": message,
        "agent": agent_name,
        "timestamp": datetime.now().isoformat()
    })

    return {"delivered": True}


def check_user_connected() -> dict:
    """Check if the user currently has the Euno app open.

    This checks if there's an active SSE connection from a client.

    Returns:
        Dict with connected boolean status
    """
    return {"connected": has_connected_clients()}
