"""
Sync - Non-destructive bidirectional synchronization.

This module provides bidirectional sync between local and remote Euno instances,
detecting changes on both sides, merging non-conflicting changes, and surfacing
conflicts for user resolution.

Public API:
    sync() - Perform bidirectional sync
    sync_init() - Initialize sync with remote
    sync_status() - Get current sync status
    list_conflicts() - List unresolved conflicts
    resolve_conflict() - Resolve a conflict
"""

from .sync import sync, sync_status, SyncResult
from .state import (
    get_sync_state,
    save_sync_state,
    get_instance_id,
    init_sync,
    SyncState,
)
from .conflicts import (
    list_conflicts,
    resolve_conflict,
    Conflict,
)
from .transport import (
    test_connection,
    Transport,
)

__all__ = [
    # Main sync operations
    "sync",
    "sync_status",
    "SyncResult",
    # State management
    "get_sync_state",
    "save_sync_state",
    "get_instance_id",
    "init_sync",
    "SyncState",
    # Conflict resolution
    "list_conflicts",
    "resolve_conflict",
    "Conflict",
    # Transport
    "test_connection",
    "Transport",
]
