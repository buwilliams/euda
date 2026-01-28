"""Consolidation commands for the core plugin."""

import os
from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


@app.command("run")
def run_cmd(
    phase: Optional[str] = typer.Option(None, "--phase", "-p", help="Phase to run: append, consolidate, or both"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: from env or 'user')"),
):
    """Run consolidation (reflection) on an agent.

    Phases:
    - append: Lightweight extraction after conversations
    - consolidate: Heavy analysis and identity updates
    - both: Run both phases (default)
    """
    from src.agent import Agent

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")

    # Create agent instance to access consolidation
    agent_instance = Agent(agent_id)

    if not agent_instance.consolidation:
        print(f"Consolidation not enabled for agent: {agent_id}")
        raise typer.Exit(1)

    effective_phase = phase or "consolidate"

    print(f"Running consolidation phase '{effective_phase}' for agent: {agent_id}")

    if effective_phase == "append":
        # Append phase requires conversation context - skip if called directly
        print("Note: Append phase requires conversation context. Skipping.")
        return

    elif effective_phase == "consolidate":
        agent_instance.consolidation.consolidate()
        print("Consolidation phase complete.")

    elif effective_phase == "both":
        # Append phase requires conversation context - skip
        agent_instance.consolidation.consolidate()
        print("Consolidation phase complete (append requires conversation context).")

    else:
        print(f"Unknown phase: {effective_phase}")
        print("Valid phases: append, consolidate, both")
        raise typer.Exit(1)
