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
from .conflicts import (
    has_unresolved_conflicts, list_conflicts, Conflict,
    Resolution, delete_conflict
)


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
    verbose: bool = False,
) -> SyncResult:
    """Perform sync with remote.

    Args:
        direction: "push", "pull", or "bidirectional"
        dry_run: If True, only show what would be done
        backup: If True, create backup before applying changes (default: True)
        verbose: If True, print progress messages

    Returns:
        SyncResult with details of the operation
    """
    def log(msg: str):
        if verbose:
            print(f"  {msg}")

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

    # Check for resolved conflicts that need to be applied
    resolved_conflicts = [c for c in list_conflicts(resolved=True) if c.resolution is not None]

    # Create transport
    transport = Transport(state.remote.host, state.remote.path)

    # Test connection
    log("Testing connection...")
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
    log("Connected")

    # Get remote instance ID
    log("Getting remote instance ID...")
    remote_instance_id = transport.get_remote_instance_id()
    if not remote_instance_id:
        # Remote might not have sync initialized - that's OK for first sync
        remote_instance_id = "unknown"

    # Import handlers here to avoid circular imports
    from .handlers import get_all_handlers

    handlers = get_all_handlers()

    # Phase 0: Apply resolved conflicts from previous sync
    if resolved_conflicts and not dry_run:
        log(f"Applying {len(resolved_conflicts)} resolved conflict(s)...")

        for conflict in resolved_conflicts:
            # Determine change type based on resolution
            if conflict.resolution == Resolution.KEEP_LOCAL:
                change_type = "push"
            elif conflict.resolution == Resolution.KEEP_REMOTE:
                change_type = "pull"
            else:
                # KEEP_NEWEST, MERGE - determine based on timestamps or content
                if conflict.resolution == Resolution.KEEP_NEWEST:
                    if conflict.local_timestamp and conflict.remote_timestamp:
                        change_type = "push" if conflict.local_timestamp >= conflict.remote_timestamp else "pull"
                    else:
                        change_type = "push"  # Default to local if no timestamps
                else:
                    # For MERGE and KEEP_BOTH, skip for now (complex cases)
                    log(f"  Skipping complex resolution: {conflict.id}")
                    continue

            # Determine handler from conflict type
            handler_name = "files"  # Default
            if conflict.type.value in ("topics", "topic_logs"):
                handler_name = "topics"
            elif conflict.type.value in ("memory_short_term", "memory_long_term"):
                handler_name = "memory"

            # Create a change to apply the resolution
            resolution_change = SyncChange(
                type=change_type,
                handler=handler_name,
                item_id=conflict.item_id,
                description=f"Apply resolved conflict: {conflict.description}",
            )

            # Apply the change
            for handler in handlers:
                if handler.name == handler_name:
                    try:
                        handler.apply_changes(transport, change_type, [resolution_change])
                        if resolution_change.applied:
                            log(f"  Applied: {conflict.item_id} ({change_type})")
                            # Delete the conflict file after successful application
                            delete_conflict(conflict.id)
                        else:
                            error_msg = resolution_change.error or "unknown reason"
                            log(f"  Failed to apply: {conflict.item_id} - {error_msg}")
                            # Delete failed conflict to prevent infinite loop
                            delete_conflict(conflict.id)
                    except Exception as e:
                        log(f"  Error applying {conflict.item_id}: {e}")
                        # Delete failed conflict to prevent infinite loop
                        delete_conflict(conflict.id)
                    break

    # Collect all changes and conflicts
    all_changes: List[SyncChange] = []
    all_conflicts: List[Conflict] = []

    # Phase 1: Detect changes from all handlers
    for handler in handlers:
        log(f"Detecting changes: {handler.name}...")
        try:
            changes, conflicts = handler.detect_changes(transport, direction)
            all_changes.extend(changes)
            all_conflicts.extend(conflicts)
            log(f"  Found {len(changes)} change(s), {len(conflicts)} conflict(s)")
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
                log("Creating local backup...")
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
                log(f"Local backup: {local_backup_name}")

        # Backup remote if we're pushing
        if direction in ("push", "bidirectional"):
            has_push = any(c.type == "push" for c in all_changes)
            if has_push:
                log("Creating remote backup...")
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
                log(f"Remote backup: {remote_backup_name}")

    # Phase 3: Apply changes
    for handler in handlers:
        log(f"Applying changes: {handler.name}...")
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
