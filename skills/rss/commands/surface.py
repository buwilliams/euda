"""RSS surfacing commands - create topics/memories from relevant posts."""

import json
import os
from datetime import datetime
from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_modules():
    """Lazy import of modules."""
    from skills.rss.lib import storage, parser
    from src.core.data.topics import create_topic
    return {
        "storage": storage,
        "parser": parser,
        "create_topic": create_topic,
    }


@app.command("check")
def check_cmd(
    feed_id: Optional[str] = typer.Argument(None, help="Feed ID to check (or all if not specified)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be surfaced without creating topics"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Check feeds and surface new posts as topics for the user.

    This creates topics for new posts so Euno can notify the user
    and potentially match them against interests.
    """
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

    surfaced = []
    now = datetime.now()

    for feed in feeds:
        fid = feed["id"]
        title = feed.get("title") or feed.get("url")
        feed_type = feed.get("type", "follow")

        result = m["parser"].fetch_feed(feed["url"])

        if "error" in result:
            if not json_output:
                print(f"Error fetching {title}: {result['error']}")
            continue

        # Find new posts
        posts = result.get("posts", [])
        post_ids = [p["id"] for p in posts if p.get("id")]
        new_ids = m["storage"].get_unseen_post_ids(fid, post_ids)
        new_posts = [p for p in posts if p.get("id") in new_ids]

        if not new_posts:
            if not json_output:
                print(f"No new posts from {title}")
            continue

        if not json_output:
            print(f"Found {len(new_posts)} new post(s) from {title}")

        for post in new_posts:
            post_title = post.get("title", "Untitled")
            post_link = post.get("link", "")
            post_content = post.get("content_text", "")[:500]  # Truncate for description

            if dry_run:
                if not json_output:
                    print(f"  Would surface: {post_title}")
                surfaced.append({
                    "feed_id": fid,
                    "feed_title": title,
                    "feed_type": feed_type,
                    "post_title": post_title,
                    "post_link": post_link,
                    "dry_run": True,
                })
                continue

            # Create topic for this post
            # Different handling for own blog vs followed feeds
            if feed_type == "own":
                # Own blog posts go to memory, not topics
                # For now, just create a topic - memory integration comes later
                topic_name = f"New blog post: {post_title}"
                topic_desc = f"You published a new post on your blog.\n\n**{post_title}**\n\n{post_content}\n\nLink: {post_link}"
                tags = ["rss", "own-blog", "notification"]
            else:
                # Followed feeds create notification topics
                topic_name = f"RSS: {post_title}"
                topic_desc = f"New post from {title}:\n\n**{post_title}**\n\n{post_content}\n\nLink: {post_link}"
                tags = ["rss", "notification", f"feed:{fid}"]

            topic = m["create_topic"](
                name=topic_name,
                description=topic_desc,
                tags=tags,
                assignee="user",  # Notify the user
                created_by="rss-skill",
            )

            # Mark post as seen
            m["storage"].mark_post_seen(fid, post["id"])

            if not json_output:
                print(f"  Surfaced: {post_title} -> topic {topic.get('id')}")

            surfaced.append({
                "feed_id": fid,
                "feed_title": title,
                "feed_type": feed_type,
                "post_title": post_title,
                "post_link": post_link,
                "topic_id": topic.get("id"),
            })

        # Update feed metadata
        m["storage"].update_feed(fid, {
            "last_checked": now.isoformat(),
        })

    if json_output:
        print(json.dumps(surfaced, indent=2))
    elif not surfaced:
        print("No new posts to surface.")
    else:
        print(f"\nSurfaced {len(surfaced)} post(s) as topics.")


@app.command("import")
def import_cmd(
    feed_id: str = typer.Argument(..., help="Feed ID to import (should be --own type)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of recent posts to import"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be imported"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Import posts from your own blog for identity bootstrapping.

    This reads recent posts and extracts themes that can be used
    to help Euno understand who you are and what you write about.
    """
    m = _get_modules()

    feed = m["storage"].get_feed(feed_id)
    if not feed:
        print(f"Feed not found: {feed_id}")
        raise typer.Exit(1)

    if feed.get("type") != "own":
        print(f"Warning: Feed '{feed.get('title')}' is not marked as your own blog.")
        print("Use 'rss feeds add <url> --own' to add your blog.")
        if not typer.confirm("Continue anyway?"):
            raise typer.Exit(0)

    result = m["parser"].fetch_feed(feed["url"])

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    posts = result.get("posts", [])[:limit]

    if not posts:
        print("No posts found in feed.")
        return

    if json_output:
        # Output structured data for further processing
        output = {
            "feed_id": feed_id,
            "feed_title": feed.get("title"),
            "feed_url": feed.get("url"),
            "posts": [
                {
                    "title": p.get("title"),
                    "published": p.get("published"),
                    "link": p.get("link"),
                    "content_preview": p.get("content_text", "")[:200],
                }
                for p in posts
            ],
        }
        print(json.dumps(output, indent=2))
        return

    print(f"Blog: {feed.get('title')}")
    print(f"Posts to import: {len(posts)}")
    print()

    # Extract themes from titles and content
    all_text = []
    for post in posts:
        title = post.get("title", "")
        content = post.get("content_text", "")
        all_text.append(f"# {title}\n\n{content[:1000]}")

        if not dry_run:
            print(f"  - {title[:60]}")

    if dry_run:
        print("Posts that would be imported:")
        for post in posts:
            print(f"  - {post.get('title', 'Untitled')[:60]}")
        print()
        print("To import, run without --dry-run")
        return

    # Create a topic with all the content for identity processing
    combined_content = "\n\n---\n\n".join(all_text)

    topic = m["create_topic"](
        name=f"Blog import: {feed.get('title')}",
        description=f"""Import {len(posts)} posts from your blog for identity bootstrapping.

The posts have been collected below. Review them to extract themes, interests,
and writing style that represent who you are.

---

{combined_content[:8000]}  # Truncate to reasonable size
""",
        tags=["rss", "own-blog", "identity-bootstrap"],
        assignee="user",
        created_by="rss-skill",
    )

    # Mark all posts as seen
    for post in posts:
        if post.get("id"):
            m["storage"].mark_post_seen(feed_id, post["id"])

    print()
    print(f"Created import topic: {topic.get('id')}")
    print("Review this topic to extract themes for your identity.")
