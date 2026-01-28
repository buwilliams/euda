"""Mastodon skill for Euno - Read public posts from Mastodon accounts."""

import sys
from pathlib import Path
from typing import Optional

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

app = typer.Typer(
    name="mastodon",
    help="Read public posts from Mastodon accounts.",
    no_args_is_help=True,
)


@app.command("posts")
def posts_cmd(
    username: str = typer.Argument(..., help="Mastodon username (without @)"),
    instance: str = typer.Option("mastodon.social", "--instance", "-i", help="Mastodon instance domain"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of posts to fetch (max 40)"),
):
    """Fetch recent public posts from a Mastodon account."""
    from skills.mastodon.lib.mastodon import get_mastodon_posts

    result = get_mastodon_posts(username=username, instance=instance, limit=limit)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Posts from @{username}@{instance} ({result.get('count', 0)} posts):")
    print()

    for post in result.get("posts", []):
        # Strip HTML tags for cleaner output
        import re
        content = re.sub(r'<[^>]+>', '', post.get("content", ""))
        content = content.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

        created = post.get("created_at", "")[:10]  # Just the date
        reblogs = post.get("reblogs_count", 0)
        favs = post.get("favourites_count", 0)

        print(f"[{created}] ({reblogs} boosts, {favs} favs)")
        print(f"  {content[:200]}{'...' if len(content) > 200 else ''}")
        print(f"  {post.get('url', '')}")
        print()


def main():
    """Entry point for the mastodon skill CLI."""
    app()


if __name__ == "__main__":
    main()
