"""Nextcloud library - WebDAV, CalDAV, and Deck API clients."""

from .client import list_instances, get_instance_config, NextcloudClient

__all__ = [
    "list_instances",
    "get_instance_config",
    "NextcloudClient",
]
