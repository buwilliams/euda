"""RSS feed and post storage."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import hashlib


def _get_skill_dir() -> Path:
    """Get the skill data directory."""
    data_dir = os.environ.get("EUNO_DATA_DIR")
    if data_dir:
        base = Path(data_dir)
    else:
        base = Path(__file__).parent.parent.parent.parent / "data"

    skill_dir = base / "skills" / "rss"
    skill_dir.mkdir(parents=True, exist_ok=True)
    return skill_dir


def _get_feeds_path() -> Path:
    """Get path to feeds storage file."""
    return _get_skill_dir() / "feeds.json"


def _get_seen_path() -> Path:
    """Get path to seen posts tracking file."""
    return _get_skill_dir() / "seen.json"


def _get_config_path() -> Path:
    """Get path to config file."""
    return _get_skill_dir() / "config.json"


def _generate_feed_id(url: str) -> str:
    """Generate a short ID from feed URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:8]


def load_config() -> dict:
    """Load skill configuration."""
    config_path = _get_config_path()
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {
        "default_check_interval_hours": 24,
        "min_check_interval_hours": 1,
        "max_check_interval_hours": 168,  # 1 week
    }


def save_config(config: dict) -> None:
    """Save skill configuration."""
    config_path = _get_config_path()
    config_path.write_text(json.dumps(config, indent=2) + "\n")


def load_feeds() -> list[dict]:
    """Load all followed feeds."""
    feeds_path = _get_feeds_path()
    if feeds_path.exists():
        data = json.loads(feeds_path.read_text())
        return data.get("feeds", [])
    return []


def save_feeds(feeds: list[dict]) -> None:
    """Save feeds list."""
    feeds_path = _get_feeds_path()
    feeds_path.write_text(json.dumps({"feeds": feeds}, indent=2) + "\n")


def get_feed(feed_id: str) -> Optional[dict]:
    """Get a specific feed by ID."""
    feeds = load_feeds()
    for feed in feeds:
        if feed.get("id") == feed_id:
            return feed
    return None


def get_feed_by_url(url: str) -> Optional[dict]:
    """Get a feed by URL."""
    feeds = load_feeds()
    for feed in feeds:
        if feed.get("url") == url:
            return feed
    return None


def add_feed(
    url: str,
    title: Optional[str] = None,
    feed_type: str = "follow",
    check_interval_hours: Optional[int] = None,
) -> dict:
    """Add a new feed to follow.

    Args:
        url: Feed URL
        title: Optional title (will be fetched from feed if not provided)
        feed_type: "follow" for others' blogs, "own" for user's blog
        check_interval_hours: Override default check interval

    Returns:
        The created feed dict
    """
    feeds = load_feeds()

    # Check if already exists
    existing = get_feed_by_url(url)
    if existing:
        return {"error": f"Feed already exists with ID: {existing['id']}"}

    config = load_config()
    feed_id = _generate_feed_id(url)

    feed = {
        "id": feed_id,
        "url": url,
        "title": title,  # Will be updated on first fetch
        "description": None,
        "type": feed_type,
        "check_interval_hours": check_interval_hours or config["default_check_interval_hours"],
        "learned_interval_hours": None,  # Calculated from post frequency
        "added_at": datetime.now().isoformat(),
        "last_checked": None,
        "last_post_at": None,
        "post_count": 0,
        "error_count": 0,
        "last_error": None,
    }

    feeds.append(feed)
    save_feeds(feeds)

    return feed


def update_feed(feed_id: str, updates: dict) -> Optional[dict]:
    """Update a feed's metadata.

    Args:
        feed_id: Feed ID to update
        updates: Dict of fields to update

    Returns:
        Updated feed or None if not found
    """
    feeds = load_feeds()

    for i, feed in enumerate(feeds):
        if feed.get("id") == feed_id:
            # Don't allow changing id or url
            updates.pop("id", None)
            updates.pop("url", None)
            feeds[i].update(updates)
            save_feeds(feeds)
            return feeds[i]

    return None


def remove_feed(feed_id: str) -> bool:
    """Remove a feed.

    Args:
        feed_id: Feed ID to remove

    Returns:
        True if removed, False if not found
    """
    feeds = load_feeds()
    original_count = len(feeds)

    feeds = [f for f in feeds if f.get("id") != feed_id]

    if len(feeds) < original_count:
        save_feeds(feeds)
        # Also clean up seen posts for this feed
        seen = load_seen()
        seen.pop(feed_id, None)
        save_seen(seen)
        return True

    return False


def load_seen() -> dict[str, list[str]]:
    """Load seen post IDs by feed.

    Returns:
        Dict mapping feed_id to list of seen post IDs
    """
    seen_path = _get_seen_path()
    if seen_path.exists():
        return json.loads(seen_path.read_text())
    return {}


def save_seen(seen: dict[str, list[str]]) -> None:
    """Save seen post IDs."""
    seen_path = _get_seen_path()
    seen_path.write_text(json.dumps(seen, indent=2) + "\n")


def mark_post_seen(feed_id: str, post_id: str) -> None:
    """Mark a post as seen.

    Args:
        feed_id: Feed the post belongs to
        post_id: Post ID (usually the post URL or guid)
    """
    seen = load_seen()
    if feed_id not in seen:
        seen[feed_id] = []
    if post_id not in seen[feed_id]:
        seen[feed_id].append(post_id)
    save_seen(seen)


def is_post_seen(feed_id: str, post_id: str) -> bool:
    """Check if a post has been seen.

    Args:
        feed_id: Feed the post belongs to
        post_id: Post ID

    Returns:
        True if seen, False otherwise
    """
    seen = load_seen()
    return post_id in seen.get(feed_id, [])


def get_unseen_post_ids(feed_id: str, post_ids: list[str]) -> list[str]:
    """Filter to only unseen post IDs.

    Args:
        feed_id: Feed the posts belong to
        post_ids: List of post IDs to check

    Returns:
        List of post IDs that haven't been seen
    """
    seen = load_seen()
    seen_ids = set(seen.get(feed_id, []))
    return [pid for pid in post_ids if pid not in seen_ids]
