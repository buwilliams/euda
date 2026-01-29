"""RSS feeds management commands."""

import json
from datetime import datetime
from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_modules():
    """Lazy import of lib modules."""
    from skills.rss.lib import storage, parser
    return {"storage": storage, "parser": parser}


@app.command("add")
def add_cmd(
    url: str = typer.Argument(..., help="Feed URL to follow"),
    own: bool = typer.Option(False, "--own", "-o", help="Mark as your own blog (for identity/memory)"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Custom title for the feed"),
    interval: Optional[int] = typer.Option(None, "--interval", "-i", help="Check interval in hours"),
):
    """Add a feed to follow."""
    m = _get_modules()

    # Check if already exists
    existing = m["storage"].get_feed_by_url(url)
    if existing:
        print(f"Feed already exists: {existing['title'] or url}")
        print(f"  ID: {existing['id']}")
        raise typer.Exit(1)

    # Fetch the feed to validate and get metadata
    print(f"Fetching feed: {url}")
    result = m["parser"].fetch_feed(url)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    # Use fetched title if not provided
    feed_title = title or result.get("title") or url

    # Estimate check interval from post frequency
    learned_interval = m["parser"].estimate_check_interval(result.get("posts", []))

    # Add the feed
    feed_type = "own" if own else "follow"
    feed = m["storage"].add_feed(
        url=url,
        title=feed_title,
        feed_type=feed_type,
        check_interval_hours=interval,
    )

    if "error" in feed:
        print(f"Error: {feed['error']}")
        raise typer.Exit(1)

    # Update with fetched metadata
    updates = {
        "title": feed_title,
        "description": result.get("description"),
        "last_checked": datetime.now().isoformat(),
        "post_count": len(result.get("posts", [])),
    }
    if learned_interval:
        updates["learned_interval_hours"] = learned_interval

    m["storage"].update_feed(feed["id"], updates)

    # Mark existing posts as seen (we only want new posts going forward)
    for post in result.get("posts", []):
        if post.get("id"):
            m["storage"].mark_post_seen(feed["id"], post["id"])

    print(f"Added feed: {feed_title}")
    print(f"  ID: {feed['id']}")
    print(f"  Type: {feed_type}")
    print(f"  Posts: {len(result.get('posts', []))}")
    if learned_interval:
        print(f"  Suggested check interval: every {learned_interval} hours (based on post frequency)")


@app.command("list")
def list_cmd(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List all followed feeds."""
    m = _get_modules()
    feeds = m["storage"].load_feeds()

    if not feeds:
        print("No feeds configured. Use 'rss feeds add <url>' to add one.")
        return

    if json_output:
        print(json.dumps(feeds, indent=2))
        return

    print(f"Following {len(feeds)} feed(s):\n")

    for feed in feeds:
        feed_type = feed.get("type", "follow")
        type_label = "[own]" if feed_type == "own" else ""

        title = feed.get("title") or feed.get("url")
        last_checked = feed.get("last_checked", "never")
        if last_checked != "never":
            last_checked = last_checked[:16].replace("T", " ")

        interval = feed.get("learned_interval_hours") or feed.get("check_interval_hours", 24)

        print(f"  {feed['id']}  {title} {type_label}")
        print(f"           URL: {feed['url']}")
        print(f"           Last checked: {last_checked} | Interval: {interval}h")
        if feed.get("last_error"):
            print(f"           Last error: {feed['last_error']}")
        print()


@app.command("remove")
def remove_cmd(
    feed_id: str = typer.Argument(..., help="Feed ID to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Stop following a feed."""
    m = _get_modules()

    feed = m["storage"].get_feed(feed_id)
    if not feed:
        print(f"Feed not found: {feed_id}")
        raise typer.Exit(1)

    if not force:
        title = feed.get("title") or feed.get("url")
        confirm = typer.confirm(f"Remove feed '{title}'?")
        if not confirm:
            print("Cancelled.")
            raise typer.Exit(0)

    if m["storage"].remove_feed(feed_id):
        print(f"Removed feed: {feed.get('title') or feed_id}")
    else:
        print(f"Failed to remove feed: {feed_id}")
        raise typer.Exit(1)


@app.command("check")
def check_cmd(
    feed_id: Optional[str] = typer.Argument(None, help="Feed ID to check (or all if not specified)"),
    force: bool = typer.Option(False, "--force", "-f", help="Check even if not due"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Check feeds for new posts."""
    m = _get_modules()

    feeds = m["storage"].load_feeds()
    if not feeds:
        print("No feeds configured.")
        return

    # Filter to specific feed if provided
    if feed_id:
        feeds = [f for f in feeds if f.get("id") == feed_id]
        if not feeds:
            print(f"Feed not found: {feed_id}")
            raise typer.Exit(1)

    results = []
    now = datetime.now()

    for feed in feeds:
        fid = feed["id"]
        title = feed.get("title") or feed.get("url")

        # Check if due (unless forced)
        if not force and feed.get("last_checked"):
            last = datetime.fromisoformat(feed["last_checked"])
            interval = feed.get("learned_interval_hours") or feed.get("check_interval_hours", 24)
            hours_since = (now - last).total_seconds() / 3600
            if hours_since < interval:
                if not json_output:
                    print(f"Skipping {title} (checked {hours_since:.1f}h ago, interval {interval}h)")
                continue

        if not json_output:
            print(f"Checking {title}...")

        result = m["parser"].fetch_feed(feed["url"])

        if "error" in result:
            # Update feed with error
            m["storage"].update_feed(fid, {
                "last_checked": now.isoformat(),
                "error_count": feed.get("error_count", 0) + 1,
                "last_error": result["error"],
            })
            if not json_output:
                print(f"  Error: {result['error']}")
            results.append({"feed_id": fid, "title": title, "error": result["error"]})
            continue

        # Find new posts
        posts = result.get("posts", [])
        post_ids = [p["id"] for p in posts if p.get("id")]
        new_ids = m["storage"].get_unseen_post_ids(fid, post_ids)
        new_posts = [p for p in posts if p.get("id") in new_ids]

        # Update learned interval
        learned = m["parser"].estimate_check_interval(posts)

        # Find most recent post date
        last_post = None
        for post in posts:
            if post.get("published"):
                if not last_post or post["published"] > last_post:
                    last_post = post["published"]

        # Update feed metadata
        updates = {
            "last_checked": now.isoformat(),
            "post_count": len(posts),
            "error_count": 0,
            "last_error": None,
        }
        if learned:
            updates["learned_interval_hours"] = learned
        if last_post:
            updates["last_post_at"] = last_post
        if result.get("title") and not feed.get("title"):
            updates["title"] = result["title"]

        m["storage"].update_feed(fid, updates)

        # Mark new posts as seen
        for post in new_posts:
            m["storage"].mark_post_seen(fid, post["id"])

        feed_result = {
            "feed_id": fid,
            "title": title,
            "type": feed.get("type", "follow"),
            "total_posts": len(posts),
            "new_posts": len(new_posts),
            "posts": new_posts if new_posts else [],
        }
        results.append(feed_result)

        if not json_output:
            if new_posts:
                print(f"  Found {len(new_posts)} new post(s):")
                for post in new_posts[:5]:  # Show first 5
                    post_title = post.get("title", "Untitled")[:60]
                    print(f"    - {post_title}")
                if len(new_posts) > 5:
                    print(f"    ... and {len(new_posts) - 5} more")
            else:
                print(f"  No new posts")

    if json_output:
        print(json.dumps(results, indent=2))


@app.command("info")
def info_cmd(
    feed_id: str = typer.Argument(..., help="Feed ID to show details"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Show detailed information about a feed."""
    m = _get_modules()

    feed = m["storage"].get_feed(feed_id)
    if not feed:
        print(f"Feed not found: {feed_id}")
        raise typer.Exit(1)

    if json_output:
        print(json.dumps(feed, indent=2))
        return

    print(f"Feed: {feed.get('title') or 'Untitled'}")
    print(f"  ID: {feed['id']}")
    print(f"  URL: {feed['url']}")
    print(f"  Type: {feed.get('type', 'follow')}")
    print(f"  Description: {feed.get('description') or 'None'}")
    print()
    print(f"  Added: {feed.get('added_at', 'Unknown')}")
    print(f"  Last checked: {feed.get('last_checked') or 'Never'}")
    print(f"  Last post: {feed.get('last_post_at') or 'Unknown'}")
    print(f"  Post count: {feed.get('post_count', 0)}")
    print()
    print(f"  Check interval: {feed.get('check_interval_hours', 24)} hours (configured)")
    if feed.get("learned_interval_hours"):
        print(f"  Learned interval: {feed['learned_interval_hours']} hours (from post frequency)")
    print()
    if feed.get("error_count", 0) > 0:
        print(f"  Errors: {feed['error_count']}")
        print(f"  Last error: {feed.get('last_error')}")
