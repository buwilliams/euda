"""RSS skill for Euno - Follow blogs and surface relevant content."""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.rss.commands import feeds, posts, surface

app = typer.Typer(
    name="rss",
    help="Follow blogs and RSS feeds to surface relevant content.",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(feeds.app, name="feeds", help="Manage followed feeds")
app.add_typer(posts.app, name="posts", help="View and search posts")
app.add_typer(surface.app, name="surface", help="Surface new posts as topics")


def main():
    """Entry point for the rss skill CLI."""
    app()


if __name__ == "__main__":
    main()
