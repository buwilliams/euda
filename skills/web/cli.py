"""Web skill for Euno - Fetch, extract, and monitor web content."""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.web.commands import fetch, save, watch

app = typer.Typer(
    name="web",
    help="Fetch, extract, and monitor web content.",
    no_args_is_help=True,
)

# Register commands
app.command(name="fetch")(fetch.fetch)
app.command(name="save")(save.save)
app.add_typer(watch.app, name="watch", help="Monitor pages for changes")


def main():
    """Entry point for the web skill CLI."""
    app()


if __name__ == "__main__":
    main()
