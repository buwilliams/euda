"""
Files Sync Handler - Hash-based file synchronization.

Handles sync of:
- Agent configs (data/agents/{id}/config.json)
- Agent identities (data/agents/{id}/identity.md)
- System config (data/system/config.json, llm.json)
- Topic assets (data/topics/assets/{topic-id}/)
- Plugin data (data/plugins/)

Uses SHA256 hashes to detect changes and conflicts.
"""

import hashlib
import json
from pathlib import Path
from typing import List, Tuple, Set, Dict, Optional

from .base import SyncHandler
from ..sync import SyncChange
from ..transport import Transport, compute_file_hash
from ..conflicts import Conflict, ConflictType, create_conflict


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

# Paths that should never be synced
NEVER_SYNC = {
    "system/auth.json",  # Site-specific passwords
    "system/sync/",  # Sync state is local
}

# Patterns to ignore (checked against path components and filenames)
IGNORE_PATTERNS = [
    "__pycache__",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    ".git",
    ".gitkeep",
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


class FilesSyncHandler(SyncHandler):
    """Handler for file-based sync (configs, identities, assets)."""

    @property
    def name(self) -> str:
        return "files"

    def detect_changes(
        self,
        transport: Transport,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Detect file changes between local and remote.

        Checks:
        - Agent configs and identities
        - System configs
        - Topic assets
        - Plugin data
        """
        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        # Check agent configs and identities
        agent_changes, agent_conflicts = self._check_agents(transport, direction)
        changes.extend(agent_changes)
        conflicts.extend(agent_conflicts)

        # Check system configs
        system_changes, system_conflicts = self._check_system_config(transport, direction)
        changes.extend(system_changes)
        conflicts.extend(system_conflicts)

        # Check topic assets
        asset_changes, asset_conflicts = self._check_assets(transport, direction)
        changes.extend(asset_changes)
        conflicts.extend(asset_conflicts)

        # Check plugin data
        plugin_changes, plugin_conflicts = self._check_plugins(transport, direction)
        changes.extend(plugin_changes)
        conflicts.extend(plugin_conflicts)

        return changes, conflicts

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

    def _check_agents(
        self,
        transport: Transport,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Check agent config and identity files."""
        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        agents_dir = DATA_DIR / "agents"
        if not agents_dir.exists():
            return changes, conflicts

        # Get local agent directories
        local_agents = set()
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir():
                local_agents.add(agent_dir.name)

        # Get remote agent directories
        remote_agents = set(transport.list_remote_files("agents"))

        # Union of all agents
        all_agents = local_agents | remote_agents

        for agent_id in all_agents:
            # Check config.json
            config_path = f"agents/{agent_id}/config.json"
            config_result = self._check_file(transport, config_path, direction)
            if config_result:
                if isinstance(config_result, Conflict):
                    conflicts.append(config_result)
                else:
                    changes.append(config_result)

            # Check identity.md
            identity_path = f"agents/{agent_id}/identity.md"
            identity_result = self._check_file(transport, identity_path, direction)
            if identity_result:
                if isinstance(identity_result, Conflict):
                    conflicts.append(identity_result)
                else:
                    changes.append(identity_result)

        return changes, conflicts

    def _check_system_config(
        self,
        transport: Transport,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Check system config files."""
        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        # Files to check
        config_files = [
            "system/config.json",
            "system/llm.json",
        ]

        for config_path in config_files:
            result = self._check_file(transport, config_path, direction)
            if result:
                if isinstance(result, Conflict):
                    conflicts.append(result)
                else:
                    changes.append(result)

        return changes, conflicts

    def _check_assets(
        self,
        transport: Transport,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Check topic asset files."""
        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        assets_dir = DATA_DIR / "topics" / "assets"
        if not assets_dir.exists():
            assets_dir.mkdir(parents=True, exist_ok=True)

        # Get local topic asset directories
        local_topics = set()
        if assets_dir.exists():
            for topic_dir in assets_dir.iterdir():
                if topic_dir.is_dir():
                    local_topics.add(topic_dir.name)

        # Get remote topic asset directories
        remote_topics = set()
        if transport.remote_directory_exists("topics/assets"):
            remote_topics = set(transport.list_remote_files("topics/assets"))

        # Union of all topics with assets
        all_topics = local_topics | remote_topics

        for topic_id in all_topics:
            topic_assets_path = f"topics/assets/{topic_id}"
            local_path = DATA_DIR / topic_assets_path

            # Get local files
            local_files = set()
            if local_path.exists():
                for f in local_path.iterdir():
                    if f.is_file():
                        local_files.add(f.name)

            # Get remote files
            remote_files = set()
            if transport.remote_directory_exists(topic_assets_path):
                remote_files = set(transport.list_remote_files(topic_assets_path))

            # Check each file
            for filename in local_files | remote_files:
                file_path = f"{topic_assets_path}/{filename}"
                result = self._check_file(transport, file_path, direction)
                if result:
                    if isinstance(result, Conflict):
                        conflicts.append(result)
                    else:
                        changes.append(result)

        return changes, conflicts

    def _check_plugins(
        self,
        transport: Transport,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Check plugin data files."""
        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        plugins_dir = DATA_DIR / "plugins"
        if not plugins_dir.exists():
            return changes, conflicts

        # Get local plugin directories
        local_plugins = set()
        for plugin_dir in plugins_dir.iterdir():
            if plugin_dir.is_dir():
                local_plugins.add(plugin_dir.name)

        # Get remote plugin directories
        remote_plugins = set()
        if transport.remote_directory_exists("plugins"):
            remote_plugins = set(transport.list_remote_files("plugins"))

        # Union of all plugins
        all_plugins = local_plugins | remote_plugins

        for plugin_name in all_plugins:
            plugin_path = f"plugins/{plugin_name}"
            local_path = DATA_DIR / plugin_path

            # Get local files
            local_files = set()
            if local_path.exists():
                for f in local_path.rglob("*"):
                    if f.is_file():
                        rel_path = f.relative_to(local_path)
                        local_files.add(str(rel_path))

            # For simplicity, just sync the whole directory if anything changed
            # by comparing directory existence and modification
            if local_files:
                # Check if remote has this plugin
                if not transport.remote_directory_exists(plugin_path):
                    if direction in ("push", "bidirectional"):
                        changes.append(SyncChange(
                            type="push",
                            handler=self.name,
                            item_id=plugin_path,
                            description=f"New plugin directory: {plugin_name}",
                        ))
                else:
                    # Check a sample of files for changes
                    for filename in list(local_files)[:5]:  # Sample up to 5 files
                        file_path = f"{plugin_path}/{filename}"
                        result = self._check_file(transport, file_path, direction)
                        if result:
                            if isinstance(result, Conflict):
                                conflicts.append(result)
                            else:
                                changes.append(result)

        return changes, conflicts

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
        for never in NEVER_SYNC:
            if relative_path.startswith(never):
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
            local_mtime = None
            remote_mtime = None
            try:
                local_mtime = local_path.stat().st_mtime
                from datetime import datetime
                local_timestamp = datetime.fromtimestamp(local_mtime).isoformat()
            except Exception:
                local_timestamp = None

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

        if direction == "push":
            # Delete remote files that don't exist locally
            deleted.extend(self._delete_remote_orphans(transport, "agents", log))
            deleted.extend(self._delete_remote_orphans(transport, "topics/assets", log))
        elif direction == "pull":
            # Delete local files that don't exist remotely
            deleted.extend(self._delete_local_orphans(transport, "agents", log))
            deleted.extend(self._delete_local_orphans(transport, "topics/assets", log))

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

        if not local_base.exists():
            return deleted

        # Get local items (directories only)
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
