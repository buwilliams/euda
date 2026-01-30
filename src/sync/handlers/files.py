"""
Files Sync Handler - Hash-based file synchronization.

Handles sync of all files under data/ directory, including:
- Agent configs and identities (data/agents/)
- System config (data/system/)
- Topic assets (data/topics/assets/)
- Skills data (data/skills/)
- Any other data subdirectories

Uses SHA256 hashes to detect changes and conflicts.
"""

import json
from pathlib import Path
from typing import List, Tuple, Set, Optional

from .base import SyncHandler
from ..sync import SyncChange
from ..transport import Transport, compute_file_hash
from ..conflicts import Conflict, ConflictType, create_conflict


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

# Paths that should never be synced (relative to data/)
NEVER_SYNC = {
    "system/auth.json",  # Site-specific passwords
    "system/sync/",  # Sync state is local
    "system/logs/",  # Local-only logs
    "topics/db.sqlite",  # Database synced separately by topics handler
    "topics/db.sqlite-journal",
    "topics/db.sqlite-wal",
    "topics/db.sqlite-shm",
}

# Patterns to ignore (checked against path components and filenames)
IGNORE_PATTERNS = [
    "__pycache__",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    ".git",
    ".gitkeep",
    ".keep",
    "node_modules",
]


def _should_ignore(path: str) -> bool:
    """Check if a path should be ignored based on patterns."""
    parts = path.split("/")
    for part in parts:
        for pattern in IGNORE_PATTERNS:
            if pattern.startswith("*"):
                # Wildcard suffix match
                if part.endswith(pattern[1:]):
                    return True
            elif part == pattern:
                return True
    return False


def _should_never_sync(path: str) -> bool:
    """Check if a path should never be synced."""
    for never in NEVER_SYNC:
        if path == never or path.startswith(never):
            return True
    return False


class FilesSyncHandler(SyncHandler):
    """Handler for file-based sync - syncs all files under data/."""

    @property
    def name(self) -> str:
        return "files"

    def detect_changes(
        self,
        transport: Transport,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Detect file changes between local and remote.

        Recursively scans all files under data/ directory.
        """
        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        # Get all local files recursively
        local_files = self._get_local_files()

        # Get all remote files recursively
        remote_files = self._get_remote_files(transport)

        # Union of all files
        all_files = local_files | remote_files

        # Check each file
        for relative_path in sorted(all_files):
            result = self._check_file(transport, relative_path, direction)
            if result:
                if isinstance(result, Conflict):
                    conflicts.append(result)
                else:
                    changes.append(result)

        return changes, conflicts

    def _get_local_files(self) -> Set[str]:
        """Get all files under data/ directory."""
        files = set()
        if not DATA_DIR.exists():
            return files

        for path in DATA_DIR.rglob("*"):
            if path.is_file():
                relative_path = str(path.relative_to(DATA_DIR))
                if not _should_ignore(relative_path) and not _should_never_sync(relative_path):
                    files.add(relative_path)

        return files

    def _get_remote_files(self, transport: Transport) -> Set[str]:
        """Get all files on remote under data/ directory."""
        return set(transport.list_remote_files_recursive(""))

    def apply_changes(
        self,
        transport: Transport,
        direction: str,
        changes: List[SyncChange],
    ) -> None:
        """Apply file changes."""
        for change in changes:
            if change.handler != self.name:
                continue
            if change.type == "conflict":
                continue  # Conflicts require resolution first

            try:
                if change.type == "push":
                    self._push_file(transport, change.item_id)
                elif change.type == "pull":
                    self._pull_file(transport, change.item_id)
                change.applied = True
            except Exception as e:
                change.error = str(e)

    def _check_file(
        self,
        transport: Transport,
        relative_path: str,
        direction: str,
    ) -> Optional[SyncChange | Conflict]:
        """Check a single file for changes.

        Returns:
            SyncChange if file needs to be synced in one direction
            Conflict if file changed on both sides
            None if file is in sync
        """
        # Skip files that should never sync
        if _should_never_sync(relative_path):
            return None

        # Skip ignored patterns (__pycache__, .DS_Store, etc.)
        if _should_ignore(relative_path):
            return None

        local_path = DATA_DIR / relative_path
        local_exists = local_path.exists()
        remote_exists = transport.remote_file_exists(relative_path)

        # Both missing - nothing to do
        if not local_exists and not remote_exists:
            return None

        # Local only - push if direction allows
        if local_exists and not remote_exists:
            if direction in ("push", "bidirectional"):
                return SyncChange(
                    type="push",
                    handler=self.name,
                    item_id=relative_path,
                    description=f"New local file: {relative_path}",
                )
            return None

        # Remote only - pull if direction allows
        if not local_exists and remote_exists:
            if direction in ("pull", "bidirectional"):
                return SyncChange(
                    type="pull",
                    handler=self.name,
                    item_id=relative_path,
                    description=f"New remote file: {relative_path}",
                )
            return None

        # Both exist - compare hashes
        local_hash = compute_file_hash(local_path)
        remote_hash = transport.get_remote_file_hash(relative_path)

        if local_hash == remote_hash:
            return None  # Files are identical

        # Files differ - determine direction or conflict
        if direction == "push":
            return SyncChange(
                type="push",
                handler=self.name,
                item_id=relative_path,
                description=f"Modified local file: {relative_path}",
            )
        elif direction == "pull":
            return SyncChange(
                type="pull",
                handler=self.name,
                item_id=relative_path,
                description=f"Modified remote file: {relative_path}",
            )
        else:
            # Bidirectional - this is a conflict
            local_content = None
            remote_content = None

            # Try to get content for conflict details
            try:
                if relative_path.endswith(".json"):
                    with open(local_path) as f:
                        local_content = json.load(f)
                    remote_text = transport.get_remote_file_content(relative_path)
                    if remote_text:
                        remote_content = json.loads(remote_text)
                else:
                    with open(local_path) as f:
                        local_content = f.read()[:1000]  # Truncate for conflict display
                    remote_content = transport.get_remote_file_content(relative_path)
                    if remote_content:
                        remote_content = remote_content[:1000]
            except Exception:
                local_content = {"hash": local_hash}
                remote_content = {"hash": remote_hash}

            # Get file modification times if possible
            try:
                local_mtime = local_path.stat().st_mtime
                from datetime import datetime, UTC
                local_timestamp = datetime.fromtimestamp(local_mtime, UTC).isoformat().replace("+00:00", "Z")
            except Exception:
                local_timestamp = None

            remote_timestamp = transport.get_remote_file_mtime(relative_path)

            # Determine conflict type
            if "config.json" in relative_path:
                conflict_type = ConflictType.AGENT_CONFIG if "agents/" in relative_path else ConflictType.SYSTEM_CONFIG
            elif "identity.md" in relative_path:
                conflict_type = ConflictType.AGENT_IDENTITY
            else:
                conflict_type = ConflictType.FILE

            return create_conflict(
                conflict_type=conflict_type,
                item_id=relative_path,
                description=f"File modified on both sides: {relative_path}",
                local=local_content,
                remote=remote_content,
                local_timestamp=local_timestamp,
                remote_timestamp=remote_timestamp,
            )

    def _push_file(self, transport: Transport, relative_path: str):
        """Push a file to remote."""
        local_path = DATA_DIR / relative_path
        result = transport.push_file(local_path, relative_path)
        if not result.success:
            raise Exception(result.error)

    def _pull_file(self, transport: Transport, relative_path: str):
        """Pull a file from remote."""
        local_path = DATA_DIR / relative_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        result = transport.fetch_file(relative_path, local_path)
        if not result.success:
            raise Exception(result.error)

    def apply_deletions(
        self,
        transport: Transport,
        direction: str,
        verbose: bool = False,
    ) -> List[str]:
        """Delete files that don't exist on the source side.

        For push: delete remote files that don't exist locally
        For pull: delete local files that don't exist remotely

        Returns list of deleted item IDs.
        """
        deleted: List[str] = []

        def log(msg: str):
            if verbose:
                print(f"    {msg}")

        # Get all top-level directories under data/
        local_top_dirs = set()
        if DATA_DIR.exists():
            for item in DATA_DIR.iterdir():
                if item.is_dir() and not _should_ignore(item.name):
                    local_top_dirs.add(item.name)

        remote_top_dirs = set()
        if transport.remote_directory_exists(""):
            remote_top_dirs = set(transport.list_remote_directories(""))

        # Union of all top-level directories
        all_top_dirs = local_top_dirs | remote_top_dirs

        if direction == "push":
            # Delete remote files/dirs that don't exist locally
            for top_dir in all_top_dirs:
                # Skip sync state directory
                if top_dir == "system":
                    # For system, only delete specific orphan subdirectories, not the whole thing
                    deleted.extend(self._delete_remote_orphan_files(transport, top_dir, log))
                else:
                    deleted.extend(self._delete_remote_orphans(transport, top_dir, log))
        elif direction == "pull":
            # Delete local files/dirs that don't exist remotely
            for top_dir in all_top_dirs:
                if top_dir == "system":
                    deleted.extend(self._delete_local_orphan_files(transport, top_dir, log))
                else:
                    deleted.extend(self._delete_local_orphans(transport, top_dir, log))

        return deleted

    def _delete_remote_orphans(
        self,
        transport: Transport,
        base_path: str,
        log,
    ) -> List[str]:
        """Delete remote files/dirs that don't exist locally."""
        deleted = []
        local_base = DATA_DIR / base_path

        # Get local items (directories only for top-level comparison)
        local_items = set()
        if local_base.exists():
            for item in local_base.iterdir():
                if item.is_dir():
                    local_items.add(item.name)

        # Get remote items (directories only) using proper directory listing
        remote_items = set()
        if transport.remote_directory_exists(base_path):
            remote_items = set(transport.list_remote_directories(base_path))

        # Find orphans (remote only) - directories that exist on remote but not locally
        orphans = remote_items - local_items

        for orphan in orphans:
            # Skip items with colons or other invalid characters (ls formatting artifacts)
            if ':' in orphan or not orphan:
                continue
            orphan_path = f"{base_path}/{orphan}"
            log(f"Deleting remote: {orphan_path}")
            try:
                transport.delete_remote_path(orphan_path)
                deleted.append(orphan_path)
            except Exception as e:
                log(f"Failed to delete {orphan_path}: {e}")

        return deleted

    def _delete_local_orphans(
        self,
        transport: Transport,
        base_path: str,
        log,
    ) -> List[str]:
        """Delete local files/dirs that don't exist remotely."""
        import shutil
        deleted = []
        local_base = DATA_DIR / base_path

        if not local_base.exists():
            return deleted

        # Get local items (directories only)
        local_items = set()
        for item in local_base.iterdir():
            if item.is_dir():
                local_items.add(item.name)

        # Get remote items (directories only)
        remote_items = set()
        if transport.remote_directory_exists(base_path):
            remote_items = set(transport.list_remote_directories(base_path))

        # Find orphans (local only) - directories that exist locally but not on remote
        orphans = local_items - remote_items

        for orphan in orphans:
            orphan_path = f"{base_path}/{orphan}"
            local_path = DATA_DIR / orphan_path
            log(f"Deleting local: {orphan_path}")
            try:
                if local_path.is_dir():
                    shutil.rmtree(local_path)
                else:
                    local_path.unlink()
                deleted.append(orphan_path)
            except Exception as e:
                log(f"Failed to delete {orphan_path}: {e}")

        return deleted

    def _delete_remote_orphan_files(
        self,
        transport: Transport,
        base_path: str,
        log,
    ) -> List[str]:
        """Delete remote files (not directories) that don't exist locally."""
        deleted = []
        local_base = DATA_DIR / base_path

        # Get local files
        local_files = set()
        if local_base.exists():
            for path in local_base.rglob("*"):
                if path.is_file():
                    rel = str(path.relative_to(DATA_DIR))
                    if not _should_never_sync(rel) and not _should_ignore(rel):
                        local_files.add(rel)

        # Get remote files
        remote_files = set()
        if transport.remote_directory_exists(base_path):
            for f in transport.list_remote_files_recursive(base_path):
                if not _should_never_sync(f) and not _should_ignore(f):
                    remote_files.add(f)

        # Find orphans
        orphans = remote_files - local_files

        for orphan in orphans:
            log(f"Deleting remote file: {orphan}")
            try:
                transport.delete_remote_path(orphan)
                deleted.append(orphan)
            except Exception as e:
                log(f"Failed to delete {orphan}: {e}")

        return deleted

    def _delete_local_orphan_files(
        self,
        transport: Transport,
        base_path: str,
        log,
    ) -> List[str]:
        """Delete local files (not directories) that don't exist remotely."""
        deleted = []
        local_base = DATA_DIR / base_path

        if not local_base.exists():
            return deleted

        # Get local files
        local_files = set()
        for path in local_base.rglob("*"):
            if path.is_file():
                rel = str(path.relative_to(DATA_DIR))
                if not _should_never_sync(rel) and not _should_ignore(rel):
                    local_files.add(rel)

        # Get remote files
        remote_files = set()
        if transport.remote_directory_exists(base_path):
            for f in transport.list_remote_files_recursive(base_path):
                if not _should_never_sync(f) and not _should_ignore(f):
                    remote_files.add(f)

        # Find orphans
        orphans = local_files - remote_files

        for orphan in orphans:
            local_path = DATA_DIR / orphan
            log(f"Deleting local file: {orphan}")
            try:
                local_path.unlink()
                deleted.append(orphan)
            except Exception as e:
                log(f"Failed to delete {orphan}: {e}")

        return deleted
