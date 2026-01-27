"""Topic management commands for the core plugin."""

from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_topics_module():
    """Lazy import of topics module to avoid circular imports."""
    from src.core.data.topics import (
        list_topics, get_topic, create_topic, update_topic,
        complete_topic, restore_topic, archive_topic, delete_topic,
        add_topic_log, get_child_topics, assign_agent, unassign_agent,
        claim_topic, release_topic, error_topic, handoff_topic
    )
    return {
        "list_topics": list_topics,
        "get_topic": get_topic,
        "create_topic": create_topic,
        "update_topic": update_topic,
        "complete_topic": complete_topic,
        "restore_topic": restore_topic,
        "archive_topic": archive_topic,
        "delete_topic": delete_topic,
        "add_topic_log": add_topic_log,
        "get_child_topics": get_child_topics,
        "assign_agent": assign_agent,
        "unassign_agent": unassign_agent,
        "claim_topic": claim_topic,
        "release_topic": release_topic,
        "error_topic": error_topic,
        "handoff_topic": handoff_topic,
    }


@app.command("list")
def list_cmd(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (todo, working, done, error, archived)"),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="Filter by assigned agent"),
    parent: Optional[str] = typer.Option(None, "--parent", "-p", help="Filter by parent topic ID"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    actionable: bool = typer.Option(False, "--actionable", help="Only show actionable topics"),
):
    """List topics with optional filters."""
    m = _get_topics_module()
    topics = m["list_topics"](
        status=status,
        parent_id=parent,
        tag=tag,
        assignee=assignee,
        actionable=actionable
    )

    if not topics:
        print("No topics found.")
        return

    for topic in topics:
        status_str = topic.get("status", "?")
        name = topic.get("name", "Untitled")
        topic_id = topic.get("id", "?")
        assignee_str = topic.get("assignee") or "-"
        print(f"[{status_str}] {name} ({topic_id}) assignee:{assignee_str}")


@app.command("get")
def get_cmd(topic_id: str = typer.Argument(..., help="Topic ID")):
    """Get detailed information about a topic."""
    m = _get_topics_module()
    topic = m["get_topic"](topic_id)

    if not topic:
        print(f"Topic not found: {topic_id}")
        raise typer.Exit(1)

    print(f"ID: {topic.get('id')}")
    print(f"Name: {topic.get('name')}")
    print(f"Status: {topic.get('status')}")
    print(f"Description: {topic.get('description') or '(none)'}")
    print(f"Parent: {topic.get('parent_id') or '(root)'}")
    print(f"Assignee: {topic.get('assignee') or '(unassigned)'}")
    print(f"Due: {topic.get('due_date') or '(no due date)'}")
    print(f"Tags: {', '.join(topic.get('tags', [])) or '(none)'}")
    print(f"Created: {topic.get('created_at')}")
    print(f"Updated: {topic.get('updated_at')}")

    log = topic.get("log", [])
    if log:
        print(f"\nLog ({len(log)} entries):")
        for entry in log[-5:]:  # Show last 5
            print(f"  [{entry.get('timestamp', '?')[:10]}] {entry.get('agent', '?')}: {entry.get('action', '?')}")


@app.command("create")
def create_cmd(
    name: str = typer.Argument(..., help="Topic name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Topic description"),
    parent: Optional[str] = typer.Option(None, "--parent", "-p", help="Parent topic ID"),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="Assign to agent"),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (YYYY-MM-DD)"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    someday: bool = typer.Option(False, "--someday", help="Mark as someday/maybe"),
):
    """Create a new topic."""
    import os
    m = _get_topics_module()

    # Get creator from environment or default
    created_by = os.environ.get("EUNO_AGENT_ID", "user")

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    topic = m["create_topic"](
        name=name,
        description=description,
        parent_id=parent,
        tags=tag_list,
        assignee=assignee,
        due_date=due,
        someday=someday,
        created_by=created_by
    )

    print(f"Created topic: {topic.get('id')}")
    print(f"Name: {topic.get('name')}")


@app.command("update")
def update_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="New status"),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="New assignee"),
    due: Optional[str] = typer.Option(None, "--due", help="New due date"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="New tags (comma-separated)"),
    someday: Optional[bool] = typer.Option(None, "--someday/--not-someday", help="Someday flag"),
):
    """Update a topic's fields."""
    m = _get_topics_module()

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    result = m["update_topic"](
        topic_id=topic_id,
        name=name,
        description=description,
        status=status,
        tags=tag_list,
        assignee=assignee,
        due_date=due,
        someday=someday
    )

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Updated topic: {topic_id}")


@app.command("complete")
def complete_cmd(topic_id: str = typer.Argument(..., help="Topic ID")):
    """Mark a topic as done."""
    import os
    m = _get_topics_module()

    agent = os.environ.get("EUNO_AGENT_ID", "user")
    result = m["complete_topic"](topic_id, agent=agent)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Completed topic: {topic_id}")


@app.command("restore")
def restore_cmd(topic_id: str = typer.Argument(..., help="Topic ID")):
    """Restore a done topic back to todo."""
    import os
    m = _get_topics_module()

    agent = os.environ.get("EUNO_AGENT_ID", "user")
    result = m["restore_topic"](topic_id, agent=agent)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Restored topic: {topic_id}")


@app.command("archive")
def archive_cmd(topic_id: str = typer.Argument(..., help="Topic ID")):
    """Archive a topic."""
    import os
    m = _get_topics_module()

    agent = os.environ.get("EUNO_AGENT_ID", "user")
    result = m["archive_topic"](topic_id, agent=agent)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Archived topic: {topic_id}")


@app.command("delete")
def delete_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    children: bool = typer.Option(False, "--children", "-c", help="Delete child topics too"),
):
    """Delete a topic permanently."""
    m = _get_topics_module()

    result = m["delete_topic"](topic_id, delete_children=children)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Deleted topic: {topic_id}")


@app.command("log")
def log_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    action: str = typer.Argument(..., help="Log message"),
):
    """Add a log entry to a topic."""
    import os
    m = _get_topics_module()

    agent = os.environ.get("EUNO_AGENT_ID", "user")
    result = m["add_topic_log"](topic_id, action, agent=agent)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Added log entry to topic: {topic_id}")


@app.command("children")
def children_cmd(parent_id: str = typer.Argument(..., help="Parent topic ID")):
    """Get child topics of a parent."""
    m = _get_topics_module()

    children = m["get_child_topics"](parent_id)

    if not children:
        print("No child topics found.")
        return

    for topic in children:
        status_str = topic.get("status", "?")
        name = topic.get("name", "Untitled")
        topic_id = topic.get("id", "?")
        print(f"[{status_str}] {name} ({topic_id})")


@app.command("assign")
def assign_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    agent_id: str = typer.Argument(..., help="Agent ID to assign"),
):
    """Assign an agent to a topic."""
    m = _get_topics_module()

    result = m["assign_agent"](topic_id, agent_id)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Assigned {agent_id} to topic: {topic_id}")


@app.command("unassign")
def unassign_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    agent_id: str = typer.Argument(..., help="Agent ID to unassign"),
):
    """Remove an agent assignment from a topic."""
    m = _get_topics_module()

    result = m["unassign_agent"](topic_id, agent_id)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Unassigned {agent_id} from topic: {topic_id}")


@app.command("claim")
def claim_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
):
    """Claim a topic for exclusive work (sets status to 'working')."""
    import os
    m = _get_topics_module()

    agent_id = os.environ.get("EUNO_AGENT_ID")
    if not agent_id:
        print("Error: EUNO_AGENT_ID environment variable not set")
        raise typer.Exit(1)

    result = m["claim_topic"](topic_id, agent_id)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Claimed topic: {topic_id}")


@app.command("release")
def release_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
):
    """Release a claimed topic (sets status back to 'todo')."""
    import os
    m = _get_topics_module()

    agent_id = os.environ.get("EUNO_AGENT_ID")
    if not agent_id:
        print("Error: EUNO_AGENT_ID environment variable not set")
        raise typer.Exit(1)

    result = m["release_topic"](topic_id, agent_id)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Released topic: {topic_id}")


@app.command("error")
def error_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    message: str = typer.Argument(..., help="Error message"),
):
    """Mark a topic as failed with an error."""
    import os
    m = _get_topics_module()

    agent = os.environ.get("EUNO_AGENT_ID", "user")
    result = m["error_topic"](topic_id, message, agent=agent)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Marked topic as error: {topic_id}")


@app.command("handoff")
def handoff_cmd(
    topic_id: str = typer.Argument(..., help="Topic ID"),
    to: str = typer.Argument(..., help="Agent ID or 'user' to hand off to"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Note about the handoff"),
):
    """Hand off a topic to another agent or user."""
    import os
    m = _get_topics_module()

    agent = os.environ.get("EUNO_AGENT_ID", "user")
    result = m["handoff_topic"](topic_id, to, note=note, agent=agent)

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Handed off topic {topic_id} to {to}")
