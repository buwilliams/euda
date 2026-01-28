"""
Unit tests for sync orchestrator.

Tests for src/sync/sync.py - the main sync() function.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestApplyResolvedConflicts:
    """Test Phase 0: applying resolved conflicts before detecting changes."""

    @pytest.fixture
    def temp_sync_dir(self, tmp_path):
        """Create temporary sync directories."""
        data_dir = tmp_path / "data"
        sync_dir = data_dir / "system" / "sync"
        conflicts_dir = sync_dir / "conflicts"
        conflicts_dir.mkdir(parents=True)

        # Create agents directory for file handler
        (data_dir / "agents" / "chat").mkdir(parents=True)

        return {
            "data_dir": data_dir,
            "sync_dir": sync_dir,
            "conflicts_dir": conflicts_dir,
        }

    @pytest.fixture
    def mock_transport_class(self):
        """Create a mock Transport class that returns a configured mock instance."""
        mock_instance = MagicMock()
        mock_instance.test_connection.return_value = (True, "OK")
        mock_instance.get_remote_instance_id.return_value = "euno-remote123"
        mock_instance.fetch_file.return_value = MagicMock(success=True)
        mock_instance.push_file.return_value = MagicMock(success=True)
        mock_instance.list_remote_files.return_value = []
        mock_instance.remote_directory_exists.return_value = False
        mock_instance.remote_file_exists.return_value = False
        mock_instance.backup_remote_data.return_value = (True, "backup-123")

        mock_class = MagicMock(return_value=mock_instance)
        return mock_class, mock_instance

    def test_resolved_conflict_keep_remote_creates_pull(self, temp_sync_dir, mock_transport_class):
        """KEEP_REMOTE resolution creates a pull change."""
        from src.sync.conflicts import ConflictType, Resolution, Conflict

        mock_class, mock_instance = mock_transport_class

        # Create a resolved conflict file
        conflict = Conflict(
            id="conflict-test123",
            type=ConflictType.AGENT_CONFIG,
            detected_at="2026-01-28T10:00:00Z",
            item_id="agents/chat/config.json",
            description="Test conflict",
            local={"state": "enabled"},
            remote={"state": "disabled"},
            resolution=Resolution.KEEP_REMOTE,
            resolved_at="2026-01-28T10:30:00Z",
        )

        conflict_file = temp_sync_dir["conflicts_dir"] / "20260128-100000-agent_config-conflict-test123.json"
        conflict_file.write_text(json.dumps(conflict.to_dict()))

        # Create local file so pull can "succeed"
        local_file = temp_sync_dir["data_dir"] / "agents" / "chat" / "config.json"
        local_file.write_text('{"state": "enabled"}')

        # Create state file
        state_file = temp_sync_dir["sync_dir"] / "state.json"
        state_file.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
            "remote": {"host": "user@server", "path": "/opt/euno"},
        }))

        from src.sync import state as state_module
        from src.sync import conflicts as conflicts_module
        from src.sync.handlers import files as files_module

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir["sync_dir"]):
            with patch.object(state_module, "STATE_PATH", state_file):
                with patch.object(conflicts_module, "CONFLICTS_DIR", temp_sync_dir["conflicts_dir"]):
                    with patch.object(files_module, "DATA_DIR", temp_sync_dir["data_dir"]):
                        with patch("src.sync.sync.Transport", mock_class):
                            from src.sync.sync import sync
                            result = sync(direction="bidirectional", dry_run=False, backup=False, verbose=False)

        # The conflict should have been applied (pull) and deleted
        assert not conflict_file.exists(), "Conflict file should be deleted after applying"

    def test_resolved_conflict_keep_local_creates_push(self, temp_sync_dir, mock_transport_class):
        """KEEP_LOCAL resolution creates a push change."""
        from src.sync.conflicts import ConflictType, Resolution, Conflict

        mock_class, mock_instance = mock_transport_class

        # Create a resolved conflict file
        conflict = Conflict(
            id="conflict-push123",
            type=ConflictType.AGENT_CONFIG,
            detected_at="2026-01-28T10:00:00Z",
            item_id="agents/chat/config.json",
            description="Test conflict",
            local={"state": "enabled"},
            remote={"state": "disabled"},
            resolution=Resolution.KEEP_LOCAL,
            resolved_at="2026-01-28T10:30:00Z",
        )

        conflict_file = temp_sync_dir["conflicts_dir"] / "20260128-100000-agent_config-conflict-push123.json"
        conflict_file.write_text(json.dumps(conflict.to_dict()))

        # Create local file so push can work
        local_file = temp_sync_dir["data_dir"] / "agents" / "chat" / "config.json"
        local_file.write_text('{"state": "enabled"}')

        state_file = temp_sync_dir["sync_dir"] / "state.json"
        state_file.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
            "remote": {"host": "user@server", "path": "/opt/euno"},
        }))

        from src.sync import state as state_module
        from src.sync import conflicts as conflicts_module
        from src.sync.handlers import files as files_module

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir["sync_dir"]):
            with patch.object(state_module, "STATE_PATH", state_file):
                with patch.object(conflicts_module, "CONFLICTS_DIR", temp_sync_dir["conflicts_dir"]):
                    with patch.object(files_module, "DATA_DIR", temp_sync_dir["data_dir"]):
                        with patch("src.sync.sync.Transport", mock_class):
                            from src.sync.sync import sync
                            result = sync(direction="bidirectional", dry_run=False, backup=False, verbose=False)

        # The conflict should have been applied (push) and deleted
        assert not conflict_file.exists(), "Conflict file should be deleted after applying"
        mock_instance.push_file.assert_called()

    def test_failed_conflict_resolution_deletes_conflict(self, temp_sync_dir, mock_transport_class):
        """Failed conflict resolution still deletes the conflict file."""
        from src.sync.conflicts import ConflictType, Resolution, Conflict

        mock_class, mock_instance = mock_transport_class
        # Mock failed fetch
        mock_instance.fetch_file.return_value = MagicMock(success=False, error="File not found")

        # Create a resolved conflict for a file that doesn't exist
        conflict = Conflict(
            id="conflict-fail123",
            type=ConflictType.AGENT_CONFIG,
            detected_at="2026-01-28T10:00:00Z",
            item_id="agents/nonexistent/config.json",
            description="Test conflict for missing file",
            local={"state": "enabled"},
            remote={"state": "disabled"},
            resolution=Resolution.KEEP_REMOTE,
            resolved_at="2026-01-28T10:30:00Z",
        )

        conflict_file = temp_sync_dir["conflicts_dir"] / "20260128-100000-agent_config-conflict-fail123.json"
        conflict_file.write_text(json.dumps(conflict.to_dict()))

        state_file = temp_sync_dir["sync_dir"] / "state.json"
        state_file.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
            "remote": {"host": "user@server", "path": "/opt/euno"},
        }))

        from src.sync import state as state_module
        from src.sync import conflicts as conflicts_module
        from src.sync.handlers import files as files_module

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir["sync_dir"]):
            with patch.object(state_module, "STATE_PATH", state_file):
                with patch.object(conflicts_module, "CONFLICTS_DIR", temp_sync_dir["conflicts_dir"]):
                    with patch.object(files_module, "DATA_DIR", temp_sync_dir["data_dir"]):
                        with patch("src.sync.sync.Transport", mock_class):
                            from src.sync.sync import sync
                            result = sync(direction="bidirectional", dry_run=False, backup=False, verbose=False)

        # Even though it failed, the conflict should be deleted to prevent infinite loop
        assert not conflict_file.exists(), "Failed conflict should still be deleted"

    def test_dry_run_skips_resolved_conflicts(self, temp_sync_dir, mock_transport_class):
        """Dry run does not apply resolved conflicts."""
        from src.sync.conflicts import ConflictType, Resolution, Conflict

        mock_class, mock_instance = mock_transport_class

        # Create a resolved conflict
        conflict = Conflict(
            id="conflict-dry123",
            type=ConflictType.AGENT_CONFIG,
            detected_at="2026-01-28T10:00:00Z",
            item_id="agents/chat/config.json",
            description="Test conflict",
            local={"state": "enabled"},
            remote={"state": "disabled"},
            resolution=Resolution.KEEP_REMOTE,
            resolved_at="2026-01-28T10:30:00Z",
        )

        conflict_file = temp_sync_dir["conflicts_dir"] / "20260128-100000-agent_config-conflict-dry123.json"
        conflict_file.write_text(json.dumps(conflict.to_dict()))

        state_file = temp_sync_dir["sync_dir"] / "state.json"
        state_file.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
            "remote": {"host": "user@server", "path": "/opt/euno"},
        }))

        from src.sync import state as state_module
        from src.sync import conflicts as conflicts_module
        from src.sync.handlers import files as files_module

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir["sync_dir"]):
            with patch.object(state_module, "STATE_PATH", state_file):
                with patch.object(conflicts_module, "CONFLICTS_DIR", temp_sync_dir["conflicts_dir"]):
                    with patch.object(files_module, "DATA_DIR", temp_sync_dir["data_dir"]):
                        with patch("src.sync.sync.Transport", mock_class):
                            from src.sync.sync import sync
                            result = sync(direction="bidirectional", dry_run=True, backup=False, verbose=False)

        # Conflict file should NOT be deleted during dry run
        assert conflict_file.exists(), "Dry run should not delete conflict files"


class TestSyncWithUnresolvedConflicts:
    """Test sync behavior when there are unresolved conflicts."""

    @pytest.fixture
    def temp_sync_dir(self, tmp_path):
        """Create temporary sync directories."""
        data_dir = tmp_path / "data"
        sync_dir = data_dir / "system" / "sync"
        conflicts_dir = sync_dir / "conflicts"
        conflicts_dir.mkdir(parents=True)
        return {
            "data_dir": data_dir,
            "sync_dir": sync_dir,
            "conflicts_dir": conflicts_dir,
        }

    def test_sync_fails_with_unresolved_conflicts(self, temp_sync_dir):
        """Sync fails when there are unresolved conflicts."""
        from src.sync.conflicts import ConflictType, Conflict

        # Create an unresolved conflict (no resolution)
        conflict = Conflict(
            id="conflict-unresolved",
            type=ConflictType.FILE,
            detected_at="2026-01-28T10:00:00Z",
            item_id="test.txt",
            description="Unresolved conflict",
            local="local content",
            remote="remote content",
            resolution=None,  # Not resolved
        )

        conflict_file = temp_sync_dir["conflicts_dir"] / "20260128-100000-file-conflict-unresolved.json"
        conflict_file.write_text(json.dumps(conflict.to_dict()))

        from src.sync import state as state_module
        from src.sync import conflicts as conflicts_module

        state_file = temp_sync_dir["sync_dir"] / "state.json"
        state_file.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
            "remote": {"host": "user@server", "path": "/opt/euno"},
        }))

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir["sync_dir"]):
            with patch.object(state_module, "STATE_PATH", state_file):
                with patch.object(conflicts_module, "CONFLICTS_DIR", temp_sync_dir["conflicts_dir"]):
                    from src.sync.sync import sync

                    result = sync(direction="bidirectional", dry_run=False, backup=False, verbose=False)

        assert result.success is False
        assert "unresolved conflict" in result.error.lower()


class TestClearResolvedConflicts:
    """Test the clear_resolved_conflicts function."""

    @pytest.fixture
    def temp_conflicts_dir(self, tmp_path):
        """Create a temporary conflicts directory."""
        conflicts_dir = tmp_path / "data" / "system" / "sync" / "conflicts"
        conflicts_dir.mkdir(parents=True)
        return conflicts_dir

    def test_clear_only_deletes_resolved(self, temp_conflicts_dir):
        """clear_resolved_conflicts only deletes resolved conflicts."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType, Resolution, Conflict

        # Create resolved conflict
        resolved = Conflict(
            id="conflict-resolved",
            type=ConflictType.FILE,
            detected_at="2026-01-28T10:00:00Z",
            item_id="resolved.txt",
            description="Resolved",
            local="local",
            remote="remote",
            resolution=Resolution.KEEP_LOCAL,
            resolved_at="2026-01-28T10:30:00Z",
        )
        resolved_file = temp_conflicts_dir / "20260128-100000-file-conflict-resolved.json"
        resolved_file.write_text(json.dumps(resolved.to_dict()))

        # Create unresolved conflict
        unresolved = Conflict(
            id="conflict-unresolved",
            type=ConflictType.FILE,
            detected_at="2026-01-28T10:00:00Z",
            item_id="unresolved.txt",
            description="Unresolved",
            local="local",
            remote="remote",
            resolution=None,
        )
        unresolved_file = temp_conflicts_dir / "20260128-100000-file-conflict-unresolved.json"
        unresolved_file.write_text(json.dumps(unresolved.to_dict()))

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            from src.sync.conflicts import clear_resolved_conflicts

            deleted = clear_resolved_conflicts()

        assert deleted == 1
        assert not resolved_file.exists(), "Resolved conflict should be deleted"
        assert unresolved_file.exists(), "Unresolved conflict should remain"
