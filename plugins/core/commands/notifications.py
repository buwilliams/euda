"""Notification commands for the core plugin."""

import os
from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_notifications_module():
    """Lazy import of notifications module."""
    from src.core.system.notifications import (
        send_chat_message, check_user_connected
    )
    return {
        "send_chat_message": send_chat_message,
        "check_user_connected": check_user_connected,
    }


@app.command("send")
def send_cmd(
    message: str = typer.Argument(..., help="Message to send"),
    agent_name: Optional[str] = typer.Option(None, "--from", "-f", help="Who the message is from"),
):
    """Send a message to the user's chat (if connected)."""
    m = _get_notifications_module()

    from_name = agent_name or os.environ.get("EUNO_AGENT_ID", "System")
    result = m["send_chat_message"](message, agent_name=from_name)

    if result.get("delivered"):
        print("Message delivered.")
    else:
        print(f"Not delivered: {result.get('reason', 'unknown')}")


@app.command("check")
def check_cmd():
    """Check if the user has the app open."""
    m = _get_notifications_module()
    result = m["check_user_connected"]()

    if result.get("connected"):
        print("User is connected.")
    else:
        print("User is not connected.")
