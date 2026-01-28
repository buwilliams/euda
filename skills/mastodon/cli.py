"""Mastodon skill for Euno - Read public posts from Mastodon accounts."""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.mastodon.commands import posts

app = typer.Typer(
    name="mastodon",
    help="Read public posts from Mastodon accounts.",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(posts.app, name="posts", help="Fetch posts from Mastodon accounts")


def main():
    """Entry point for the mastodon skill CLI."""
    app()


if __name__ == "__main__":
    main()
