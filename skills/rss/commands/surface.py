"""RSS surfacing commands - create topics/memories from relevant posts."""

import json
import os
from datetime import datetime
from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_modules():
    """Lazy import of modules."""
    from skills.rss.lib import storage, parser, matching
    from src.core.data.topics import create_topic
    from src.core.data.memory import add_memory
    return {
        "storage": storage,
        "parser": parser,
        "matching": matching,
        "create_topic": create_topic,
        "add_memory": add_memory,
    }


def _create_blog_post_memory(m: dict, post: dict, feed_title: str) -> dict:
    """Create a short-term memory for a blog post.

    Args:
        m: Modules dict
        post: Post dict with title, link, content_text, published
        feed_title: Name of the blog

    Returns:
        Created memory entry
    """
    post_title = post.get("title", "Untitled")
    post_link = post.get("link", "")
    published = post.get("published", "")[:10] if post.get("published") else ""

    # Create a concise description for memory
    description = f"Wrote blog post: {post_title}"
    if post_link:
        description += f" ({post_link})"

    return m["add_memory"](
        short_description=description,
        type="idea",  # Blog posts represent ideas you've articulated
        agent_id="user",
    )


@app.command("check")
def check_cmd(
    feed_id: Optional[str] = typer.Argument(None, help="Feed ID to check (or all if not specified)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be surfaced without creating topics"),
    all_posts: bool = typer.Option(False, "--all", "-a", help="Surface all matching posts (ignore exploration matching for own blogs)"),
    full_content: bool = typer.Option(False, "--full", "-F", help="Fetch full page content for matching (slower but more accurate)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Check feeds and surface relevant new posts as topics.

    Only posts matching active explorations are surfaced (unless --all).
    Own blog posts are always surfaced for memory/identity tracking.
    Use --full to fetch complete article content for better matching.
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

    # Load explorations for matching
    explorations = m["matching"].load_explorations()
    if not explorations and not all_posts:
        print("No active explorations found. Posts will only be surfaced from --own feeds.")
        print("Create explorations or use --all to surface everything.")

    surfaced = []
    skipped = []
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

            # Fetch full content if requested (for better matching)
            if full_content and post_link:
                if not json_output:
                    print(f"  Fetching full content for: {post_title[:40]}...")
                full_result = m["parser"].fetch_full_content(post_link)
                if "error" not in full_result:
                    post["content_text"] = full_result.get("content_text", post.get("content_text", ""))

            post_content = post.get("content_text", "")[:500]  # Truncate for description

            # Own blog posts always match
            if feed_type == "own":
                match_result = m["matching"].MatchResult(
                    matched=True,
                    match_reason="Own blog - always surfaced",
                )
            elif all_posts:
                match_result = m["matching"].MatchResult(
                    matched=True,
                    match_reason="--all flag set",
                )
            else:
                # Check if post matches any exploration
                match_result = m["matching"].match_post(post, explorations)

            if not match_result.matched:
                # Skip non-matching posts
                if not json_output and not dry_run:
                    print(f"  Skipped: {post_title[:50]}... ({match_result.match_reason})")
                skipped.append({
                    "feed_id": fid,
                    "post_title": post_title,
                    "reason": match_result.match_reason,
                    "score": match_result.score,
                })
                # Still mark as seen so we don't re-check
                m["storage"].mark_post_seen(fid, post["id"])
                continue

            if dry_run:
                if not json_output:
                    print(f"  Would surface: {post_title[:50]}")
                    print(f"    Match: {match_result.match_reason}")
                surfaced.append({
                    "feed_id": fid,
                    "feed_title": title,
                    "feed_type": feed_type,
                    "post_title": post_title,
                    "post_link": post_link,
                    "match_reason": match_result.match_reason,
                    "exploration": match_result.exploration_name,
                    "dry_run": True,
                })
                continue

            # Create topic for this post
            if feed_type == "own":
                topic_name = f"New blog post: {post_title}"
                topic_desc = f"You published a new post on your blog.\n\n**{post_title}**\n\n{post_content}\n\nLink: {post_link}"
                tags = ["rss", "own-blog", "notification"]

                # Also add to memory - own blog posts represent your ideas
                memory = _create_blog_post_memory(m, post, title)
                if not json_output:
                    print(f"    Added to memory: {memory.get('id')}")
            else:
                # Include exploration context in the topic
                exp_context = ""
                if match_result.exploration_name:
                    exp_context = f"\n\n*Matched exploration: {match_result.exploration_name}*\n*{match_result.match_reason}*"

                topic_name = f"RSS: {post_title}"
                topic_desc = f"New post from {title}:\n\n**{post_title}**\n\n{post_content}{exp_context}\n\nLink: {post_link}"
                tags = ["rss", "notification", f"feed:{fid}"]
                if match_result.exploration_id:
                    tags.append(f"exploration:{match_result.exploration_id}")

            topic = m["create_topic"](
                name=topic_name,
                description=topic_desc,
                tags=tags,
                assignee="user",
                created_by="rss-skill",
            )

            # Mark post as seen
            m["storage"].mark_post_seen(fid, post["id"])

            if not json_output:
                print(f"  Surfaced: {post_title[:50]} -> topic {topic.get('id')}")
                if match_result.exploration_name:
                    print(f"    Matched: {match_result.exploration_name}")

            surfaced_entry = {
                "feed_id": fid,
                "feed_title": title,
                "feed_type": feed_type,
                "post_title": post_title,
                "post_link": post_link,
                "topic_id": topic.get("id"),
                "match_reason": match_result.match_reason,
                "exploration": match_result.exploration_name,
            }
            if feed_type == "own":
                surfaced_entry["memory_id"] = memory.get("id") if memory else None
            surfaced.append(surfaced_entry)

        # Update feed metadata
        m["storage"].update_feed(fid, {
            "last_checked": now.isoformat(),
        })

    if json_output:
        print(json.dumps({"surfaced": surfaced, "skipped": skipped}, indent=2))
    else:
        if surfaced:
            print(f"\nSurfaced {len(surfaced)} post(s) as topics.")
        if skipped:
            print(f"Skipped {len(skipped)} non-matching post(s).")
        if not surfaced and not skipped:
            print("No new posts found.")


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
        print(f"Would create {len(posts)} memory entries (type: idea)")
        print("To import, run without --dry-run")
        return

    # Create memories for each blog post
    print("\nCreating memories for blog posts...")
    memories_created = 0
    for post in posts:
        try:
            memory = _create_blog_post_memory(m, post, feed.get("title"))
            memories_created += 1
            if not json_output:
                print(f"  + {post.get('title', 'Untitled')[:50]} -> {memory.get('id')}")
        except Exception as e:
            print(f"  ! Failed to create memory for '{post.get('title')}': {e}")

    # Create a topic with all the content for identity processing
    combined_content = "\n\n---\n\n".join(all_text)

    topic = m["create_topic"](
        name=f"Blog import: {feed.get('title')}",
        description=f"""Import {len(posts)} posts from your blog for identity bootstrapping.

{memories_created} memories created (type: idea) to track these posts.

The posts have been collected below. Review them to extract themes, interests,
and writing style that represent who you are.

---

{combined_content[:8000]}
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
    print(f"Created {memories_created} memories")
    print(f"Created import topic: {topic.get('id')}")
    print("Review the topic to extract themes for your identity.")


@app.command("analyze")
def analyze_cmd(
    feed_id: Optional[str] = typer.Argument(None, help="Feed ID to analyze (or all if not specified)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of posts to analyze per feed"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Analyze how feed posts match against explorations.

    Shows which posts would match and why, useful for tuning.
    Does not mark posts as seen or create topics.
    """
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

    # Load explorations
    explorations = m["matching"].load_explorations()

    if not json_output:
        print(f"Active explorations ({len(explorations)}):")
        for exp in explorations:
            print(f"  - {exp['name']}")
            themes = exp['themes']
            if themes['phrases']:
                print(f"    Phrases: {', '.join(themes['phrases'][:3])}")
            if themes['name_tokens']:
                print(f"    Keywords: {', '.join(sorted(themes['name_tokens'])[:5])}")
        print()

    all_results = []

    for feed in feeds:
        title = feed.get("title") or feed.get("url")
        feed_type = feed.get("type", "follow")

        if not json_output:
            print(f"Analyzing: {title} (type: {feed_type})")

        result = m["parser"].fetch_feed(feed["url"])
        if "error" in result:
            if not json_output:
                print(f"  Error: {result['error']}")
            continue

        posts = result.get("posts", [])[:limit]
        analysis = m["matching"].analyze_feed_matches(posts, explorations)

        if json_output:
            analysis["feed_id"] = feed["id"]
            analysis["feed_title"] = title
            analysis["feed_type"] = feed_type
            all_results.append(analysis)
            continue

        print(f"  Total posts: {analysis['total_posts']}")
        print(f"  Matched: {analysis['matched_posts']}")
        print(f"  Unmatched: {analysis['unmatched_posts']}")

        if analysis['matches']:
            print(f"\n  Matches:")
            for match in analysis['matches'][:5]:
                print(f"    + {match['title'][:50]}")
                print(f"      -> {match['exploration']} (score: {match['score']:.1f})")
                print(f"      {match['reason']}")

        if analysis['non_matches']:
            print(f"\n  Non-matches (showing first 3):")
            for non in analysis['non_matches'][:3]:
                print(f"    - {non['title'][:50]}")
                print(f"      {non['reason']}")

        print()

    if json_output:
        print(json.dumps(all_results, indent=2))


@app.command("explorations")
def explorations_cmd(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Show active explorations and their matching themes.

    Displays what keywords and phrases will be used for matching.
    """
    m = _get_modules()

    explorations = m["matching"].load_explorations()

    if not explorations:
        print("No active explorations found.")
        print("Create explorations in Euno to enable content matching.")
        return

    if json_output:
        # Include theme details
        output = []
        for exp in explorations:
            output.append({
                "id": exp["id"],
                "name": exp["name"],
                "description": exp["description"][:200] if exp["description"] else "",
                "themes": {
                    "phrases": exp["themes"]["phrases"],
                    "keywords": sorted(exp["themes"]["keywords"]),
                    "name_keywords": sorted(exp["themes"]["name_tokens"]),
                },
            })
        print(json.dumps(output, indent=2))
        return

    print(f"Active explorations ({len(explorations)}):\n")

    for exp in explorations:
        print(f"  {exp['name']}")
        print(f"  ID: {exp['id']}")
        if exp["description"]:
            print(f"  Description: {exp['description'][:100]}...")

        themes = exp["themes"]
        print(f"  Matching:")
        if themes["phrases"]:
            print(f"    Phrases: {', '.join(themes['phrases'])}")
        if themes["name_tokens"]:
            print(f"    From name: {', '.join(sorted(themes['name_tokens']))}")
        desc_keywords = themes["keywords"] - themes["name_tokens"]
        if desc_keywords:
            kw_list = sorted(desc_keywords)[:10]
            print(f"    From description: {', '.join(kw_list)}")
            if len(desc_keywords) > 10:
                print(f"    ... and {len(desc_keywords) - 10} more")
        print()
