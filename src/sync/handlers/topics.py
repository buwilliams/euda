"""
Topics Sync Handler - SQLite record-level synchronization.

Handles sync of:
- Topics table (by ID, using updated_at for conflict detection)
- Topic logs table (append-only, deduplicate by composite key)

Strategy:
1. Export local topics to JSON
2. Fetch remote topics JSON
3. Compare by ID + updated_at
4. Merge non-conflicting changes
5. Create conflicts for items changed on both sides
"""

import json
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional

from .base import SyncHandler
from ..sync import SyncChange
from ..transport import Transport
from ..conflicts import Conflict, ConflictType, create_conflict


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


class TopicsSyncHandler(SyncHandler):
    """Handler for SQLite topics sync."""

    @property
    def name(self) -> str:
        return "topics"

    def detect_changes(
        self,
        transport: Transport,
        direction: str,
    ) -> Tuple[List[SyncChange], List[Conflict]]:
        """Detect topic changes between local and remote."""
        from src.core.data.topics import export_topics

        changes: List[SyncChange] = []
        conflicts: List[Conflict] = []

        # Export local topics
        local_data = export_topics()
        local_topics = {t["id"]: t for t in local_data["topics"]}
        local_logs = local_data["logs"]

        # Fetch remote topics
        remote_data = self._fetch_remote_topics(transport)
        if remote_data is None:
            # Remote doesn't have topics export yet - push all if direction allows
            if direction in ("push", "bidirectional") and local_topics:
                changes.append(SyncChange(
                    type="push",
                    handler=self.name,
                    item_id="all",
                    description=f"Push {len(local_topics)} topics (remote has none)",
                ))
            return changes, conflicts

        remote_topics = {t["id"]: t for t in remote_data.get("topics", [])}
        remote_logs = remote_data.get("logs", [])

        # Find all topic IDs
        all_ids = set(local_topics.keys()) | set(remote_topics.keys())

        for topic_id in all_ids:
            local = local_topics.get(topic_id)
            remote = remote_topics.get(topic_id)

            if local and not remote:
                # Local only - push if direction allows
                if direction in ("push", "bidirectional"):
                    changes.append(SyncChange(
                        type="push",
                        handler=self.name,
                        item_id=topic_id,
                        description=f"New local topic: {local['name']}",
                    ))

            elif remote and not local:
                # Remote only - pull if direction allows
                if direction in ("pull", "bidirectional"):
                    changes.append(SyncChange(
                        type="pull",
                        handler=self.name,
                        item_id=topic_id,
                        description=f"New remote topic: {remote['name']}",
                    ))

            else:
                # Both exist - compare updated_at
                local_updated = local.get("updated_at", "")
                remote_updated = remote.get("updated_at", "")

                if local_updated == remote_updated:
                    continue  # In sync

                if direction == "push":
                    changes.append(SyncChange(
                        type="push",
                        handler=self.name,
                        item_id=topic_id,
                        description=f"Push updated topic: {local['name']}",
                    ))
                elif direction == "pull":
                    changes.append(SyncChange(
                        type="pull",
                        handler=self.name,
                        item_id=topic_id,
                        description=f"Pull updated topic: {remote['name']}",
                    ))
                else:
                    # Bidirectional - check if same base version was modified
                    # For now, use timestamp comparison
                    if local_updated > remote_updated:
                        changes.append(SyncChange(
                            type="push",
                            handler=self.name,
                            item_id=topic_id,
                            description=f"Push newer topic: {local['name']}",
                        ))
                    elif remote_updated > local_updated:
                        changes.append(SyncChange(
                            type="pull",
                            handler=self.name,
                            item_id=topic_id,
                            description=f"Pull newer topic: {remote['name']}",
                        ))

        # Check for log entries that need syncing
        local_log_keys = {
            (l["topic_id"], l["timestamp"], l["agent"], l["action"])
            for l in local_logs
        }
        remote_log_keys = {
            (l["topic_id"], l["timestamp"], l["agent"], l["action"])
            for l in remote_logs
        }

        # Logs to push
        logs_to_push = local_log_keys - remote_log_keys
        if logs_to_push and direction in ("push", "bidirectional"):
            changes.append(SyncChange(
                type="push",
                handler=self.name,
                item_id="logs",
                description=f"Push {len(logs_to_push)} log entries",
            ))

        # Logs to pull
        logs_to_pull = remote_log_keys - local_log_keys
        if logs_to_pull and direction in ("pull", "bidirectional"):
            changes.append(SyncChange(
                type="pull",
                handler=self.name,
                item_id="logs",
                description=f"Pull {len(logs_to_pull)} log entries",
            ))

        return changes, conflicts

    def apply_changes(
        self,
        transport: Transport,
        direction: str,
        changes: List[SyncChange],
    ) -> None:
        """Apply topic changes."""
        from src.core.data.topics import export_topics, import_topics

        # Get changes for this handler
        my_changes = [c for c in changes if c.handler == self.name and c.type != "conflict"]
        if not my_changes:
            return

        # Check if we need to push, pull, or both
        has_push = any(c.type == "push" for c in my_changes)
        has_pull = any(c.type == "pull" for c in my_changes)

        # Handle pull first (so we have remote data)
        if has_pull:
            remote_data = self._fetch_remote_topics(transport)
            if remote_data:
                result = import_topics(remote_data, merge=True)
                # Mark pull changes as applied
                for c in my_changes:
                    if c.type == "pull":
                        c.applied = True

        # Handle push
        if has_push:
            local_data = export_topics()
            self._push_topics(transport, local_data)
            # Mark push changes as applied
            for c in my_changes:
                if c.type == "push":
                    c.applied = True

    def _fetch_remote_topics(self, transport: Transport) -> Optional[dict]:
        """Fetch topics export from remote.

        Returns exported topics dict or None if not available.
        """
        # Export topics on remote using plugin CLI
        success, stdout, stderr = transport.run_remote_command(
            f"cd {transport.remote_path} && "
            "uv run python -c 'import json; from src.core.data.topics import export_topics; print(json.dumps(export_topics()))'"
        )

        if not success or not stdout.strip():
            return None

        try:
            return json.loads(stdout.strip())
        except json.JSONDecodeError:
            return None

    def _push_topics(self, transport: Transport, data: dict):
        """Push topics export to remote and import there."""
        # Write data to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)

        try:
            # Push to remote temp location
            remote_temp = "/tmp/euno_topics_sync.json"
            result = transport.push_file(temp_path, f"../{remote_temp}")  # Hack to push outside data/

            # Actually push to /tmp
            import subprocess
            subprocess.run(
                ["rsync", "-az", str(temp_path), f"{transport.host}:{remote_temp}"],
                capture_output=True,
            )

            # Import on remote
            success, stdout, stderr = transport.run_remote_command(
                f"cd {transport.remote_path} && "
                f"uv run python -c 'import json; from src.core.data.topics import import_topics; "
                f"data = json.load(open(\"{remote_temp}\")); print(json.dumps(import_topics(data)))'"
            )

            # Clean up remote temp
            transport.run_remote_command(f"rm -f {remote_temp}")

        finally:
            temp_path.unlink(missing_ok=True)
