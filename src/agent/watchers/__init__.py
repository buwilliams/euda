"""
Watchers Module - Monitor content sources for agent interests.

Watchers periodically check content sources (calendar, mastodon) for content
that matches agent interests. When matches are found, observation topics
are created for the relevant agents.

Chat observation is handled separately via an inline hook (not a periodic watcher)
since it needs to be real-time.
"""

from .base import (
    Watcher,
    WatcherRegistry,
    create_observation_topic,
    process_observations,
)
from .calendar import CalendarWatcher
from .mastodon import MastodonWatcher

# Global registry of watchers
registry = WatcherRegistry()
registry.register(CalendarWatcher())
registry.register(MastodonWatcher())

__all__ = [
    "Watcher",
    "WatcherRegistry",
    "CalendarWatcher",
    "MastodonWatcher",
    "registry",
    "create_observation_topic",
    "process_observations",
]
