"""Mastodon posts command."""

import re
from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_mastodon_module():
    """Lazy import of mastodon module."""
    from skills.mastodon.lib.mastodon import get_mastodon_posts
    return {"get_mastodon_posts": get_mastodon_posts}


@app.command("list")
def list_cmd(
    username: str = typer.Argument(..., help="Mastodon username (without @)"),
    instance: str = typer.Option("mastodon.social", "--instance", "-i", help="Mastodon instance domain"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of posts to fetch (max 40)"),
):
    """Fetch recent public posts from a Mastodon account."""
    m = _get_mastodon_module()
    result = m["get_mastodon_posts"](username=username, instance=instance, limit=limit)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Posts from @{username}@{instance} ({result.get('count', 0)} posts):")
    print()

    for post in result.get("posts", []):
        # Strip HTML tags for cleaner output
        content = re.sub(r'<[^>]+>', '', post.get("content", ""))
        content = content.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

        created = post.get("created_at", "")[:10]  # Just the date
        reblogs = post.get("reblogs_count", 0)
        favs = post.get("favourites_count", 0)

        print(f"[{created}] ({reblogs} boosts, {favs} favs)")
        print(f"  {content[:200]}{'...' if len(content) > 200 else ''}")
        print(f"  {post.get('url', '')}")
        print()
