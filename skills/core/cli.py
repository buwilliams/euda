"""Core skill for Euno - Topic management, memory, agents, and system operations."""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.core.commands import topics, assets, memory, identity, agents, consolidate, dates, notifications, quote, done, store, delegation

app = typer.Typer(
    name="core",
    help="Core Euno operations: topics, memory, agents, and more.",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(topics.app, name="topics", help="Topic management commands")
app.add_typer(assets.app, name="assets", help="Topic asset management")
app.add_typer(memory.app, name="memory", help="Memory operations")
app.add_typer(identity.app, name="identity", help="Identity management")
app.add_typer(agents.app, name="agents", help="Agent management")
app.add_typer(consolidate.app, name="consolidate", help="Consolidation operations")
app.add_typer(dates.app, name="dates", help="Date utilities")
app.add_typer(notifications.app, name="notify", help="Notification commands")
app.add_typer(quote.app, name="quote", help="Quote generation")
app.add_typer(store.app, name="store", help="Import files to long-term memory")
app.add_typer(delegation.app, name="delegation", help="Task delegation to other agents")

# Register standalone commands
app.command(name="done")(done.done_working)


def main():
    """Entry point for the core skill CLI."""
    app()


if __name__ == "__main__":
    main()
