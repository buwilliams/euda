"""Google Calendar integration plugin - Multiple account support for Google Calendar."""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from plugins.gcal.commands import accounts, calendars, events

app = typer.Typer(
    name="gcal",
    help="Google Calendar integration with multiple account support.",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(accounts.app, name="accounts", help="Manage Google accounts")
app.add_typer(calendars.app, name="calendars", help="List calendars")
app.add_typer(events.app, name="events", help="Event operations")


def main():
    """Entry point for the Google Calendar plugin CLI."""
    app()


if __name__ == "__main__":
    main()
