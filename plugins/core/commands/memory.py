"""Memory management commands for the core plugin."""

import os
from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)

VALID_TYPES = {"person", "place", "thing", "goal", "concern", "idea", "learning", "behavior"}


def _get_memory_module():
    """Lazy import of memory module."""
    from plugins.core.data.memory import (
        add_memory, list_memory, remove_memory,
        write_long_term_memory, graduate_memory,
        recall_memory, analyze_memory
    )
    return {
        "add_memory": add_memory,
        "list_memory": list_memory,
        "remove_memory": remove_memory,
        "write_long_term_memory": write_long_term_memory,
        "graduate_memory": graduate_memory,
        "recall_memory": recall_memory,
        "analyze_memory": analyze_memory,
    }


@app.command("add")
def add_cmd(
    description: str = typer.Argument(..., help="Brief description of what to remember"),
    type: str = typer.Option(..., "--type", "-t", help=f"Category: {', '.join(sorted(VALID_TYPES))}"),
    expected: Optional[str] = typer.Option(None, "--expected", "-e", help="Expected date (YYYY-MM-DD)"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: user)"),
):
    """Add an item to short-term memory."""
    m = _get_memory_module()

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")

    if type not in VALID_TYPES:
        print(f"Error: Invalid type. Must be one of: {', '.join(sorted(VALID_TYPES))}")
        raise typer.Exit(1)

    result = m["add_memory"](
        short_description=description,
        type=type,
        date_expected=expected,
        agent_id=agent_id
    )

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Added memory: {result.get('id')}")
    print(f"Type: {result.get('type')}")
    print(f"Description: {result.get('short_description')}")


@app.command("list")
def list_cmd(
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: user)"),
):
    """List all valid short-term memory items."""
    m = _get_memory_module()

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")
    items = m["list_memory"](agent_id=agent_id)

    if not items:
        print("No memory items found.")
        return

    # Group by type
    by_type = {}
    for item in items:
        t = item.get("type", "idea")
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(item)

    for type_name in sorted(by_type.keys()):
        print(f"\n{type_name.upper()}:")
        for item in by_type[type_name]:
            date_info = f"mentioned {item.get('date_mentioned', '?')}"
            if item.get("date_expected"):
                date_info += f", expected {item['date_expected']}"
            print(f"  [{item.get('id')}] {item.get('short_description')} ({date_info})")


@app.command("remove")
def remove_cmd(
    entry_id: str = typer.Argument(..., help="Memory entry ID (e.g., mem-abc12345)"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: user)"),
):
    """Remove a short-term memory item."""
    m = _get_memory_module()

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")
    result = m["remove_memory"](entry_id, agent_id=agent_id)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Removed memory: {entry_id}")


@app.command("graduate")
def graduate_cmd(
    memory_id: str = typer.Argument(..., help="Memory entry ID to graduate"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Reason for graduating"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: user)"),
):
    """Graduate a short-term memory item to long-term memory."""
    m = _get_memory_module()

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")
    result = m["graduate_memory"](memory_id, reason=reason, agent_id=agent_id)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Graduated memory: {memory_id}")
    print(f"Type: {result.get('type')}")
    print(f"Description: {result.get('description')}")


@app.command("write-long-term")
def write_long_term_cmd(
    content: str = typer.Argument(..., help="Content to add to long-term memory"),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Date (YYYY-MM-DD, default: today)"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Source attribution"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: user)"),
):
    """Add an entry to long-term memory."""
    m = _get_memory_module()

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")
    result = m["write_long_term_memory"](
        content=content,
        date=date,
        agent_id=agent_id,
        source=source
    )

    print(f"Added to long-term memory for {result.get('date')}")


@app.command("recall")
def recall_cmd(
    query: str = typer.Argument(..., help="What to recall (semantic search)"),
    days: int = typer.Option(365, "--days", "-d", help="How far back to search"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: user)"),
):
    """Recall information from long-term memory using semantic search."""
    m = _get_memory_module()

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")
    result = m["recall_memory"](
        query=query,
        time_range_days=days,
        agent_id=agent_id
    )

    if result.get("error"):
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Query: {result.get('query')}")
    print(f"\nFindings:\n{result.get('findings')}")

    sources = result.get("sources", [])
    if sources:
        print(f"\nSources ({len(sources)}):")
        for src in sources[:5]:
            print(f"  [{src.get('date', '?')}] {src.get('snippet', '')[:80]}...")


@app.command("analyze")
def analyze_cmd(
    query: str = typer.Argument(..., help="What pattern to analyze"),
    days: int = typer.Option(365, "--days", "-d", help="Analysis window"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent ID (default: user)"),
):
    """Analyze patterns and trends in long-term memory."""
    m = _get_memory_module()

    agent_id = agent or os.environ.get("EUNO_AGENT_ID", "user")
    result = m["analyze_memory"](
        query=query,
        time_range_days=days,
        agent_id=agent_id
    )

    if result.get("error"):
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Query: {result.get('query')}")
    print(f"\nAnalysis:\n{result.get('findings')}")

    sources = result.get("sources", [])
    if sources:
        print(f"\nSources ({len(sources)}):")
        for src in sources[:5]:
            print(f"  [{src.get('date', '?')}] {src.get('snippet', '')[:80]}...")
