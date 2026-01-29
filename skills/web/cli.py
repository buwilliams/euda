"""Web skill for Euno - Save and monitor web content.

For fetching/extracting web content, use: web_search extract <url>
"""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.web.commands import save, watch

app = typer.Typer(
    name="web",
    help="Save and monitor web content. For extraction, use: web_search extract <url>",
    no_args_is_help=True,
)

# Register commands
app.command(name="save")(save.save)
app.add_typer(watch.app, name="watch", help="Monitor pages for changes")


def main():
    """Entry point for the web skill CLI."""
    app()


if __name__ == "__main__":
    main()
