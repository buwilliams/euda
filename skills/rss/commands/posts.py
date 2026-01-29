"""RSS posts viewing commands."""

import json
from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_modules():
    """Lazy import of lib modules."""
    from skills.rss.lib import storage, parser
    return {"storage": storage, "parser": parser}


@app.command("list")
def list_cmd(
    feed_id: Optional[str] = typer.Option(None, "--feed", "-f", help="Filter to specific feed"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of posts to show"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List recent posts from feeds."""
    m = _get_modules()

    feeds = m["storage"].load_feeds()
    if not feeds:
        print("No feeds configured.")
        return

    if feed_id:
        feeds = [f for f in feeds if f.get("id") == feed_id]
        if not feeds:
            print(f"Feed not found: {feed_id}")
            raise typer.Exit(1)

    all_posts = []

    for feed in feeds:
        result = m["parser"].fetch_feed(feed["url"])
        if "error" in result:
            if not json_output:
                print(f"Error fetching {feed.get('title', feed['url'])}: {result['error']}")
            continue

        for post in result.get("posts", []):
            post["feed_id"] = feed["id"]
            post["feed_title"] = feed.get("title") or feed["url"]
            post["feed_type"] = feed.get("type", "follow")
            all_posts.append(post)

    # Sort by published date (newest first)
    all_posts.sort(key=lambda p: p.get("published") or "", reverse=True)

    # Limit
    all_posts = all_posts[:limit]

    if json_output:
        print(json.dumps(all_posts, indent=2))
        return

    if not all_posts:
        print("No posts found.")
        return

    print(f"Recent posts:\n")

    for post in all_posts:
        title = post.get("title", "Untitled")[:70]
        feed_title = post.get("feed_title", "Unknown")
        published = (post.get("published") or "")[:10]
        link = post.get("link", "")

        print(f"  [{published}] {title}")
        print(f"           From: {feed_title}")
        if link:
            print(f"           {link}")
        print()


@app.command("show")
def show_cmd(
    feed_id: str = typer.Argument(..., help="Feed ID"),
    post_index: int = typer.Option(0, "--index", "-i", help="Post index (0 = most recent)"),
    full: bool = typer.Option(False, "--full", "-F", help="Fetch full content from post URL (not just RSS summary)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Show full content of a post."""
    m = _get_modules()

    feed = m["storage"].get_feed(feed_id)
    if not feed:
        print(f"Feed not found: {feed_id}")
        raise typer.Exit(1)

    result = m["parser"].fetch_feed(feed["url"])
    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    posts = result.get("posts", [])
    if not posts:
        print("No posts in feed.")
        return

    if post_index >= len(posts):
        print(f"Post index {post_index} out of range (0-{len(posts) - 1})")
        raise typer.Exit(1)

    post = posts[post_index]

    # Fetch full content if requested
    if full and post.get("link"):
        if not json_output:
            print(f"Fetching full content from {post['link']}...")
        full_result = m["parser"].fetch_full_content(post["link"])
        if "error" not in full_result:
            post["content"] = full_result.get("content", post.get("content", ""))
            post["content_text"] = full_result.get("content_text", post.get("content_text", ""))
            post["full_content_fetched"] = True
        elif not json_output:
            print(f"Warning: Could not fetch full content: {full_result['error']}")

    if json_output:
        print(json.dumps(post, indent=2))
        return

    print(f"Title: {post.get('title', 'Untitled')}")
    print(f"Published: {post.get('published', 'Unknown')}")
    print(f"Author: {post.get('author') or 'Unknown'}")
    print(f"Link: {post.get('link', 'None')}")
    if post.get("full_content_fetched"):
        print("(Full content fetched from URL)")
    print()
    print("=" * 60)
    print()

    # Show plain text content
    content = post.get("content_text", "")
    if content:
        # Word wrap at ~80 chars
        words = content.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > 80:
                print(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            print(line)
    else:
        print("(No content)")


@app.command("content")
def content_cmd(
    url: str = typer.Argument(..., help="Post URL to fetch full content from"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Fetch full article content from a post URL.

    RSS feeds often only include summaries. This fetches the actual
    web page and extracts the main article content.
    """
    m = _get_modules()

    if not json_output:
        print(f"Fetching: {url}")

    result = m["parser"].fetch_full_content(url)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(result, indent=2))
        return

    content = result.get("content_text", "")
    print(f"\nContent ({len(content)} chars):\n")
    print("=" * 60)
    print()

    if content:
        # Word wrap at ~80 chars
        words = content.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > 80:
                print(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            print(line)
    else:
        print("(No content extracted)")


@app.command("fetch")
def fetch_cmd(
    url: str = typer.Argument(..., help="Feed URL to fetch (without adding)"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of posts to show"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Fetch and preview a feed without adding it."""
    m = _get_modules()

    print(f"Fetching: {url}")
    result = m["parser"].fetch_feed(url)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(result, indent=2))
        return

    print(f"\nFeed: {result.get('title', 'Untitled')}")
    print(f"Format: {result.get('format', 'unknown')}")
    print(f"Description: {result.get('description') or 'None'}")
    print(f"Link: {result.get('link', 'None')}")
    print(f"Posts: {len(result.get('posts', []))}")

    # Estimate check interval
    learned = m["parser"].estimate_check_interval(result.get("posts", []))
    if learned:
        print(f"Suggested check interval: {learned} hours")

    posts = result.get("posts", [])[:limit]
    if posts:
        print(f"\nRecent posts:")
        for post in posts:
            title = post.get("title", "Untitled")[:60]
            published = (post.get("published") or "")[:10]
            print(f"  [{published}] {title}")
