"""Identity management commands for the core plugin."""

import os
from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_identity_module():
    """Lazy import of identity module."""
    from src.core.data.identity import (
        get_identity, update_identity
    )
    return {
        "get_identity": get_identity,
        "update_identity": update_identity,
    }


@app.command("show")
def show_cmd(
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: user)"),
):
    """Show an agent's identity."""
    m = _get_identity_module()

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")
    result = m["get_identity"](agent_id=agent_id)

    if not result.get("exists"):
        print(f"No identity found for: {agent_id}")
        return

    print(result.get("content", ""))


@app.command("update")
def update_cmd(
    content: str = typer.Argument(..., help="New identity content"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: user)"),
):
    """Update an agent's identity."""
    m = _get_identity_module()

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")
    result = m["update_identity"](agent_id=agent_id, content=content)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Updated identity for: {agent_id}")
