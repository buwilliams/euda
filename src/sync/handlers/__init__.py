"""
Sync Handlers - Data-type specific sync logic.

Each handler knows how to:
1. Detect changes between local and remote
2. Detect conflicts
3. Apply changes in both directions
"""

from typing import List

from .base import SyncHandler


def get_all_handlers() -> List[SyncHandler]:
    """Get all sync handlers in the order they should be processed.

    Returns:
        List of SyncHandler instances
    """
    from .files import FilesSyncHandler
    from .topics import TopicsSyncHandler
    from .memory import MemorySyncHandler

    return [
        # Files first (configs, identities, assets)
        FilesSyncHandler(),
        # Topics (SQLite database)
        TopicsSyncHandler(),
        # Memory (short-term JSONL, long-term markdown)
        MemorySyncHandler(),
    ]


__all__ = ["get_all_handlers", "SyncHandler"]
