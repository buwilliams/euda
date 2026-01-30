"""Web skill for Euno - Search, extract, save, and monitor web content."""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.web.commands import search, extract, save, watch, preview

app = typer.Typer(
    name="web",
    help="Search, extract, save, and monitor web content.",
    no_args_is_help=True,
)

# Register commands
app.command(name="search")(search.search)
app.command(name="extract")(extract.extract)
app.command(name="save")(save.save)
app.command(name="preview")(preview.preview)
app.add_typer(watch.app, name="watch", help="Monitor pages for changes")


def main():
    """Entry point for the web skill CLI."""
    app()


if __name__ == "__main__":
    main()
