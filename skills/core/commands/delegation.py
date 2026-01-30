"""Delegation command for the core plugin."""

import os
from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_topics_module():
    """Lazy import of topics module to avoid circular imports."""
    from src.core.data.topics import create_topic
    return {"create_topic": create_topic}


@app.command("delegate")
def delegate_task(
    task: str = typer.Argument(..., help="Description of the task to delegate"),
    to_agent: str = typer.Option("soul", "--to", "-t", help="Target agent (default: soul)"),
    response: Optional[str] = typer.Option(None, "--response", "-r", help="Conversational response to show the user"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Detailed task description"),
):
    """Delegate a time-consuming task to another agent.

    Creates a topic assigned to the target agent with the 'delegated' and
    'user:request' tags. Optionally prints an immediate conversational
    response to acknowledge the delegation.

    Use this for tasks that would take multiple steps or significant time:
    - Research: finding information, comparing options, investigating topics
    - Generation: writing code, documents, summaries, analyses
    - Multi-step tasks: anything requiring multiple tool calls or phases
    - External operations: file processing, API calls, integrations

    Examples:
        delegate "Research RAG best practices 2026" --response "I'll research that for you."
        delegate "Write a summary of the meeting notes" --to soul
        delegate "Analyze the codebase structure" -d "Map out all modules and their dependencies"
    """
    m = _get_topics_module()

    # Get creator from environment
    created_by = os.environ.get("EUNO_AGENT_ID", "user")

    # Build tags for tracking
    tags = ["delegated", "user:request"]

    # Create the topic assigned to the target agent
    topic = m["create_topic"](
        name=task,
        description=description,
        assignee=to_agent,
        tags=tags,
        created_by=created_by
    )

    # Print conversational response if provided
    if response:
        print(response)

    # Always print delegation confirmation
    print(f"[Delegated to {to_agent}: {topic.get('id')}]")
