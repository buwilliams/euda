"""
Sync - Main synchronization orchestrator.

Coordinates all sync handlers to perform bidirectional sync between
local and remote Euno instances.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Optional, Dict, Any

from .state import get_sync_state, record_sync, SyncState
from .transport import Transport, backup_local_data
from .conflicts import has_unresolved_conflicts, list_conflicts, Conflict


DATA_DIR = Path(__file__).parent.parent.parent / "data"


@dataclass
class SyncChange:
    """A single change detected or applied during sync."""
    type: str  # "push", "pull", "conflict"
    handler: str  # Handler name (e.g., "topics", "files", "memory")
    item_id: str  # ID of the changed item
    description: str
    applied: bool = False
    error: Optional[str] = None


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    direction: str  # "push", "pull", or "bidirectional"
    dry_run: bool
    changes: List[SyncChange] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    error: Optional[str] = None
    started_at: str = ""
    completed_at: str = ""
    local_backup: str = ""  # Name of local backup created (if any)
    remote_backup: str = ""  # Name of remote backup created (if any)

    @property
    def changes_pushed(self) -> int:
        """Count of changes pushed to remote."""
        return len([c for c in self.changes if c.type == "push" and c.applied])

    @property
    def changes_pulled(self) -> int:
        """Count of changes pulled from remote."""
        return len([c for c in self.changes if c.type == "pull" and c.applied])

    @property
    def conflict_count(self) -> int:
        """Count of conflicts detected."""
        return len([c for c in self.changes if c.type == "conflict"])

    def summary(self) -> str:
        """Human-readable summary of the sync result."""
        lines = []

        if self.dry_run:
            lines.append("Dry run - no changes applied")

        if self.error:
            lines.append(f"Error: {self.error}")
            return "\n".join(lines)

        if self.direction in ("bidirectional", "push"):
            pushed = len([c for c in self.changes if c.type == "push"])
            lines.append(f"Push: {pushed} change(s)")

        if self.direction in ("bidirectional", "pull"):
            pulled = len([c for c in self.changes if c.type == "pull"])
            lines.append(f"Pull: {pulled} change(s)")

        conflicts = len([c for c in self.changes if c.type == "conflict"])
        if conflicts:
            lines.append(f"Conflicts: {conflicts} (use 'sync conflicts' to view)")

        if not lines:
            lines.append("No changes")

        return "\n".join(lines)


def sync(
    direction: str = "bidirectional",
    dry_run: bool = False,
    backup: bool = True,
) -> SyncResult:
    """Perform sync with remote.

    Args:
        direction: "push", "pull", or "bidirectional"
        dry_run: If True, only show what would be done
        backup: If True, create backup before applying changes (default: True)

    Returns:
        SyncResult with details of the operation
    """
    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    local_backup_name = ""
    remote_backup_name = ""

    # Get current state
    state = get_sync_state()

    # Auto-configure from EUNO_SERVER env var if no remote set
    if not state.remote:
        import os
        server = os.environ.get("EUNO_SERVER")
        if server:
            from .state import init_sync
            state = init_sync(server)
        else:
            return SyncResult(
                success=False,
                direction=direction,
                dry_run=dry_run,
                error="No remote configured. Set EUNO_SERVER in .env or run 'sync init <server>'.",
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            )

    # Check for unresolved conflicts from previous sync
    if has_unresolved_conflicts():
        unresolved = list_conflicts(resolved=False)
        return SyncResult(
            success=False,
            direction=direction,
            dry_run=dry_run,
            error=f"There are {len(unresolved)} unresolved conflict(s). Resolve them first with 'sync conflicts'.",
            started_at=started_at,
            completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )

    # Create transport
    transport = Transport(state.remote.host, state.remote.path)

    # Test connection
    connected, message = transport.test_connection()
    if not connected:
        return SyncResult(
            success=False,
            direction=direction,
            dry_run=dry_run,
            error=f"Cannot connect to remote: {message}",
            started_at=started_at,
            completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )

    # Get remote instance ID
    remote_instance_id = transport.get_remote_instance_id()
    if not remote_instance_id:
        # Remote might not have sync initialized - that's OK for first sync
        remote_instance_id = "unknown"

    # Collect all changes and conflicts
    all_changes: List[SyncChange] = []
    all_conflicts: List[Conflict] = []

    # Import handlers here to avoid circular imports
    from .handlers import get_all_handlers

    handlers = get_all_handlers()

    # Phase 1: Detect changes from all handlers
    for handler in handlers:
        try:
            changes, conflicts = handler.detect_changes(transport, direction)
            all_changes.extend(changes)
            all_conflicts.extend(conflicts)
        except Exception as e:
            return SyncResult(
                success=False,
                direction=direction,
                dry_run=dry_run,
                error=f"Error detecting changes in {handler.name}: {e}",
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            )

    # If dry run or conflicts, don't apply changes
    if dry_run or all_conflicts:
        completed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return SyncResult(
            success=len(all_conflicts) == 0,
            direction=direction,
            dry_run=dry_run,
            changes=all_changes,
            conflicts=all_conflicts,
            started_at=started_at,
            completed_at=completed_at,
        )

    # Phase 2: Create backups before applying changes
    if backup and all_changes:
        # Backup local if we're pulling
        if direction in ("pull", "bidirectional"):
            has_pull = any(c.type == "pull" for c in all_changes)
            if has_pull:
                success, result = backup_local_data()
                if not success:
                    return SyncResult(
                        success=False,
                        direction=direction,
                        dry_run=dry_run,
                        changes=all_changes,
                        error=f"Failed to create local backup: {result}",
                        started_at=started_at,
                        completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    )
                local_backup_name = result

        # Backup remote if we're pushing
        if direction in ("push", "bidirectional"):
            has_push = any(c.type == "push" for c in all_changes)
            if has_push:
                success, result = transport.backup_remote_data()
                if not success:
                    return SyncResult(
                        success=False,
                        direction=direction,
                        dry_run=dry_run,
                        changes=all_changes,
                        error=f"Failed to create remote backup: {result}",
                        started_at=started_at,
                        completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    )
                remote_backup_name = result

    # Phase 3: Apply changes
    for handler in handlers:
        try:
            handler.apply_changes(transport, direction, all_changes)
        except Exception as e:
            return SyncResult(
                success=False,
                direction=direction,
                dry_run=dry_run,
                changes=all_changes,
                error=f"Error applying changes in {handler.name}: {e}",
                started_at=started_at,
                completed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            )

    # Record sync
    completed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    if not dry_run:
        record_sync(
            remote_instance_id=remote_instance_id,
            success=True,
            direction=direction,
            changes_pushed=len([c for c in all_changes if c.type == "push" and c.applied]),
            changes_pulled=len([c for c in all_changes if c.type == "pull" and c.applied]),
        )

    return SyncResult(
        success=True,
        direction=direction,
        dry_run=dry_run,
        changes=all_changes,
        conflicts=all_conflicts,
        started_at=started_at,
        completed_at=completed_at,
        local_backup=local_backup_name,
        remote_backup=remote_backup_name,
    )


def sync_status() -> Dict[str, Any]:
    """Get current sync status.

    Returns:
        Dictionary with status information
    """
    state = get_sync_state()
    unresolved = list_conflicts(resolved=False)

    status = {
        "instance_id": state.instance_id,
        "remote_configured": state.remote is not None,
        "unresolved_conflicts": len(unresolved),
    }

    if state.remote:
        status["remote_host"] = state.remote.host
        status["remote_path"] = state.remote.path

    if state.last_sync:
        status["last_sync"] = {
            "timestamp": state.last_sync.timestamp,
            "remote_instance_id": state.last_sync.remote_instance_id,
            "success": state.last_sync.success,
            "direction": state.last_sync.direction,
            "changes_pushed": state.last_sync.changes_pushed,
            "changes_pulled": state.last_sync.changes_pulled,
        }

    return status
