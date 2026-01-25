"""
Mastodon Watcher - Monitor user's Mastodon posts for relevant content.
"""

import json
import logging
import re
from pathlib import Path

from .base import Watcher

logger = logging.getLogger(__name__)

# Config location for Mastodon settings
CONFIG_FILE = Path(__file__).parent.parent.parent.parent / "data" / "system" / "mastodon.json"


class MastodonWatcher(Watcher):
    """Watches user's Mastodon posts for content matching agent interests.

    Requires configuration in data/system/mastodon.json:
    {
        "username": "yourname",
        "instance": "mastodon.social"
    }
    """

    source_name = "mastodon"

    def _load_config(self) -> dict:
        """Load Mastodon configuration."""
        if not CONFIG_FILE.exists():
            return {}
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            return {}

    def is_configured(self) -> bool:
        """Check if Mastodon is configured."""
        config = self._load_config()
        return bool(config.get("username") and config.get("instance"))

    def fetch_content(self) -> list[dict]:
        """Fetch recent Mastodon posts.

        Returns:
            List of post content items
        """
        config = self._load_config()
        if not config:
            return []

        username = config.get("username")
        instance = config.get("instance")

        try:
            from ...tools.integration.mastodon import get_mastodon_posts
        except ImportError:
            logger.debug("Mastodon tools not available")
            return []

        result = get_mastodon_posts(username=username, instance=instance, limit=20)

        if "error" in result:
            logger.debug(f"Mastodon fetch error: {result['error']}")
            return []

        posts = result.get("posts", [])
        content_items = []

        for post in posts:
            # Strip HTML from content
            content = post.get("content", "")
            text = self._strip_html(content)

            if text:
                content_items.append({
                    "id": post.get("id", ""),
                    "text": text,
                    "timestamp": post.get("created_at")
                })

        return content_items

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from content.

        Args:
            html: HTML string

        Returns:
            Plain text
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
