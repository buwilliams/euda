"""Prompt management commands for the core skill."""

from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_prompts_module():
    """Lazy import of prompts module."""
    from src.core.data.prompts import (
        list_prompts,
        get_prompt,
        update_prompt,
        reset_prompt,
        AVAILABLE_PROMPTS,
    )
    return {
        "list_prompts": list_prompts,
        "get_prompt": get_prompt,
        "update_prompt": update_prompt,
        "reset_prompt": reset_prompt,
        "AVAILABLE_PROMPTS": AVAILABLE_PROMPTS,
    }


def _get_agent_id() -> str:
    """Get current agent ID from environment."""
    import os
    return os.environ.get("EUNO_AGENT_ID", "user")


@app.command("list")
def list_cmd(
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: current agent)"),
):
    """List available prompts and their override status.

    Shows all prompts that can be customized, indicating which have
    agent-specific overrides.
    """
    m = _get_prompts_module()
    agent_id = agent or _get_agent_id()

    prompts = m["list_prompts"](agent_id)

    print(f"Prompts for agent: {agent_id}\n")

    # Group by category
    agent_prompts = [p for p in prompts if p["name"] in ["system", "topic", "topic_assignment", "continue", "continue_with_context", "progress_check", "consolidation"]]
    consolidation_prompts = [p for p in prompts if p["name"] not in [p["name"] for p in agent_prompts]]

    print("Agent Prompts:")
    for p in agent_prompts:
        override = "[override]" if p["has_override"] else ""
        status = "ok" if p["exists"] else "missing"
        print(f"  {p['name']:25} {status:8} {override}")

    print("\nConsolidation Prompts:")
    for p in consolidation_prompts:
        override = "[override]" if p["has_override"] else ""
        status = "ok" if p["exists"] else "missing"
        print(f"  {p['name']:25} {status:8} {override}")


@app.command("show")
def show_cmd(
    name: str = typer.Argument(..., help="Prompt name (e.g., 'system', 'topic_assignment')"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: current agent)"),
):
    """Show the content of a prompt.

    Displays the agent's version if an override exists, otherwise the system default.
    """
    m = _get_prompts_module()
    agent_id = agent or _get_agent_id()

    result = m["get_prompt"](agent_id, name)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Prompt: {result['name']}")
    print(f"Source: {result['source']}")
    print(f"Path: {result['path']}")
    print("-" * 40)
    print(result["content"])


@app.command("update")
def update_cmd(
    name: str = typer.Argument(..., help="Prompt name to update"),
    content: str = typer.Argument(..., help="New prompt content (use \\n for newlines)"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: current agent)"),
):
    """Update a prompt with custom content.

    Creates an agent-specific override. The system default remains unchanged.
    Use 'prompts reset' to revert to the system default.

    Content supports \\n for newlines. Variables like {identity} and {tools_by_type}
    will be substituted at runtime.

    Example:
        prompts update system "## Identity\\n{identity}\\n\\n## Tools\\n{tools_by_type}"
    """
    m = _get_prompts_module()
    agent_id = agent or _get_agent_id()

    # Convert escaped newlines to actual newlines
    content = content.replace("\\n", "\n")

    result = m["update_prompt"](agent_id, name, content)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Updated prompt: {result['name']}")
    print(f"Path: {result['path']}")
    if result.get("previous"):
        print("(Previous content was backed up)")


@app.command("reset")
def reset_cmd(
    name: str = typer.Argument(..., help="Prompt name to reset"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: current agent)"),
):
    """Reset a prompt to the system default.

    Removes any agent-specific override, reverting to the system prompt.
    """
    m = _get_prompts_module()
    agent_id = agent or _get_agent_id()

    result = m["reset_prompt"](agent_id, name)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    if result["removed_override"]:
        print(f"Reset prompt: {result['name']}")
        print("Reverted to system default")
    else:
        print(f"No override exists for: {result['name']}")
        print("Already using system default")


@app.command("diff")
def diff_cmd(
    name: str = typer.Argument(..., help="Prompt name to compare"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: current agent)"),
):
    """Show the difference between system default and agent override.

    Useful for understanding what customizations have been made.
    """
    import difflib
    from src.core.data.prompts import AVAILABLE_PROMPTS, SYSTEM_PROMPTS_DIR, AGENTS_DIR, DATA_DIR
    from pathlib import Path

    agent_id = agent or _get_agent_id()

    if name not in AVAILABLE_PROMPTS:
        print(f"Error: Unknown prompt: {name}")
        raise typer.Exit(1)

    rel_path = AVAILABLE_PROMPTS[name]
    filename = Path(rel_path).name

    system_path = SYSTEM_PROMPTS_DIR / rel_path
    override_path = AGENTS_DIR / agent_id / "prompts" / filename

    if not system_path.exists():
        print(f"Error: System prompt not found: {name}")
        raise typer.Exit(1)

    if not override_path.exists():
        print(f"No override exists for: {name}")
        print("Agent is using the system default")
        return

    system_content = system_path.read_text().splitlines()
    override_content = override_path.read_text().splitlines()

    diff = difflib.unified_diff(
        system_content,
        override_content,
        fromfile=f"system/{name}",
        tofile=f"override/{name}",
        lineterm=""
    )

    diff_text = "\n".join(diff)
    if diff_text:
        print(diff_text)
    else:
        print("No differences (override is identical to system default)")
