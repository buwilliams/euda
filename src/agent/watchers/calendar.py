"""
Calendar Watcher - Monitor Nextcloud calendar for relevant events.
"""

import logging
from datetime import datetime, timedelta

from .base import Watcher

logger = logging.getLogger(__name__)


class CalendarWatcher(Watcher):
    """Watches Nextcloud calendar for events matching agent interests.

    Checks upcoming events (next 7 days) and creates observations when
    event titles or descriptions match agent interests.
    """

    source_name = "calendar"

    def is_configured(self) -> bool:
        """Check if Nextcloud is configured."""
        try:
            from ...tools.integration.nextcloud.client import get_client
            get_client()
            return True
        except Exception:
            return False

    def fetch_content(self) -> list[dict]:
        """Fetch upcoming calendar events.

        Returns:
            List of event content items
        """
        try:
            from ...tools.integration.nextcloud.calendar import nc_list_events
        except ImportError:
            logger.debug("Nextcloud calendar tools not available")
            return []

        # Fetch events for next 7 days
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        result = nc_list_events(start_date=start_date, end_date=end_date)

        if "error" in result:
            logger.debug(f"Calendar fetch error: {result['error']}")
            return []

        events = result.get("events", [])
        content_items = []

        for event in events:
            # Combine title and description for matching
            title = event.get("summary", "")
            description = event.get("description", "")
            text = f"{title} {description}".strip()

            if text:
                content_items.append({
                    "id": event.get("uid", event.get("summary", "")),
                    "text": text,
                    "timestamp": event.get("start")
                })

        return content_items
