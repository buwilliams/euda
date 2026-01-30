"""
Unit tests for sync files handler.

Tests for src/sync/handlers/files.py
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestShouldIgnore:
    """Test _should_ignore function."""

    def test_ignore_pycache_directory(self):
        """Ignores __pycache__ directories."""
        from src.sync.handlers.files import _should_ignore

        assert _should_ignore("skills/core/__pycache__/cli.cpython-311.pyc") is True
        assert _should_ignore("__pycache__/test.pyc") is True
        assert _should_ignore("src/__pycache__/module.py") is True

    def test_ignore_ds_store(self):
        """Ignores .DS_Store files."""
        from src.sync.handlers.files import _should_ignore

        assert _should_ignore(".DS_Store") is True
        assert _should_ignore("topics/assets/.DS_Store") is True
        assert _should_ignore("agents/chat/.DS_Store") is True

    def test_ignore_pyc_files(self):
        """Ignores .pyc files."""
        from src.sync.handlers.files import _should_ignore

        assert _should_ignore("test.pyc") is True
        assert _should_ignore("src/module.pyc") is True
        assert _should_ignore("skills/plugin.pyc") is True

    def test_ignore_pyo_files(self):
        """Ignores .pyo files."""
        from src.sync.handlers.files import _should_ignore

        assert _should_ignore("test.pyo") is True
        assert _should_ignore("src/optimized.pyo") is True

    def test_ignore_git_directory(self):
        """Ignores .git directories."""
        from src.sync.handlers.files import _should_ignore

        assert _should_ignore(".git") is True
        assert _should_ignore(".git/config") is True
        assert _should_ignore(".git/objects/abc123") is True

    def test_ignore_gitkeep(self):
        """Ignores .gitkeep files."""
        from src.sync.handlers.files import _should_ignore

        assert _should_ignore(".gitkeep") is True
        assert _should_ignore("topics/assets/.gitkeep") is True

    def test_ignore_node_modules(self):
        """Ignores node_modules directories."""
        from src.sync.handlers.files import _should_ignore

        assert _should_ignore("node_modules") is True
        assert _should_ignore("node_modules/package/index.js") is True
        assert _should_ignore("web/node_modules/react/index.js") is True

    def test_allow_normal_files(self):
        """Allows normal files through."""
        from src.sync.handlers.files import _should_ignore

        assert _should_ignore("agents/chat/config.json") is False
        assert _should_ignore("agents/chat/identity.md") is False
        assert _should_ignore("system/config.json") is False
        assert _should_ignore("topics/assets/topic-123/file.txt") is False
        assert _should_ignore("skills/core/cli.py") is False

    def test_allow_similar_names(self):
        """Allows files with similar but not matching names."""
        from src.sync.handlers.files import _should_ignore

        # These look similar but shouldn't match patterns
        assert _should_ignore("my_pycache_file.txt") is False
        assert _should_ignore("DS_Store_backup.txt") is False
        assert _should_ignore("gitkeep_notes.md") is False


class TestNeverSync:
    """Test NEVER_SYNC paths."""

    def test_never_sync_auth(self):
        """Never syncs auth.json."""
        from src.sync.handlers.files import NEVER_SYNC

        assert any("auth.json" in p for p in NEVER_SYNC)

    def test_never_sync_sync_state(self):
        """Never syncs sync state directory."""
        from src.sync.handlers.files import NEVER_SYNC

        assert any("sync/" in p for p in NEVER_SYNC)


class TestFilesSyncHandler:
    """Test FilesSyncHandler class."""

    def test_handler_name(self):
        """Handler has correct name."""
        from src.sync.handlers.files import FilesSyncHandler

        handler = FilesSyncHandler()

        assert handler.name == "files"


class TestCheckFile:
    """Test _check_file method."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "data"
        (data_dir / "agents" / "chat").mkdir(parents=True)
        (data_dir / "system").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.remote_file_exists.return_value = False
        transport.get_remote_file_hash.return_value = None
        transport.get_remote_file_content.return_value = None
        transport.get_remote_file_mtime.return_value = None
        return transport

    def test_check_file_skips_never_sync(self, temp_data_dir, mock_transport):
        """_check_file skips NEVER_SYNC paths."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            result = handler._check_file(mock_transport, "system/auth.json", "push")

            assert result is None

    def test_check_file_skips_ignored(self, temp_data_dir, mock_transport):
        """_check_file skips ignored patterns."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            result = handler._check_file(mock_transport, "skills/__pycache__/test.pyc", "push")

            assert result is None

    def test_check_file_local_only_push(self, temp_data_dir, mock_transport):
        """_check_file creates push change for local-only file."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler
        from src.sync.sync import SyncChange

        # Create local file
        config_path = temp_data_dir / "agents" / "chat" / "config.json"
        config_path.write_text('{"id": "chat"}')

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            result = handler._check_file(mock_transport, "agents/chat/config.json", "push")

            assert isinstance(result, SyncChange)
            assert result.type == "push"
            assert "New local file" in result.description

    def test_check_file_local_only_pull_no_change(self, temp_data_dir, mock_transport):
        """_check_file returns None for local-only in pull direction."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler

        # Create local file
        config_path = temp_data_dir / "agents" / "chat" / "config.json"
        config_path.write_text('{"id": "chat"}')

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            result = handler._check_file(mock_transport, "agents/chat/config.json", "pull")

            assert result is None

    def test_check_file_remote_only_pull(self, temp_data_dir, mock_transport):
        """_check_file creates pull change for remote-only file."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler
        from src.sync.sync import SyncChange

        mock_transport.remote_file_exists.return_value = True

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            result = handler._check_file(mock_transport, "agents/worker/config.json", "pull")

            assert isinstance(result, SyncChange)
            assert result.type == "pull"
            assert "New remote file" in result.description

    def test_check_file_both_exist_same_hash(self, temp_data_dir, mock_transport):
        """_check_file returns None when hashes match."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler
        from src.sync.transport import compute_file_hash

        # Create local file
        config_path = temp_data_dir / "agents" / "chat" / "config.json"
        config_path.write_text('{"id": "chat"}')

        # Mock remote with same hash
        local_hash = compute_file_hash(config_path)
        mock_transport.remote_file_exists.return_value = True
        mock_transport.get_remote_file_hash.return_value = local_hash

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            result = handler._check_file(mock_transport, "agents/chat/config.json", "push")

            assert result is None

    def test_check_file_both_exist_different_hash_push(self, temp_data_dir, mock_transport):
        """_check_file creates push change when hashes differ in push mode."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler
        from src.sync.sync import SyncChange

        # Create local file
        config_path = temp_data_dir / "agents" / "chat" / "config.json"
        config_path.write_text('{"id": "chat", "local": true}')

        # Mock remote with different hash
        mock_transport.remote_file_exists.return_value = True
        mock_transport.get_remote_file_hash.return_value = "different_hash_abc123"

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            result = handler._check_file(mock_transport, "agents/chat/config.json", "push")

            assert isinstance(result, SyncChange)
            assert result.type == "push"
            assert "Modified local file" in result.description

    def test_check_file_both_exist_different_hash_bidirectional_conflict(self, temp_data_dir, mock_transport):
        """_check_file creates conflict in bidirectional mode when hashes differ."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler
        from src.sync.conflicts import Conflict

        # Create local file
        config_path = temp_data_dir / "agents" / "chat" / "config.json"
        config_path.write_text('{"id": "chat", "local": true}')

        # Mock remote with different hash and content
        mock_transport.remote_file_exists.return_value = True
        mock_transport.get_remote_file_hash.return_value = "different_hash_abc123"
        mock_transport.get_remote_file_content.return_value = '{"id": "chat", "remote": true}'
        mock_transport.get_remote_file_mtime.return_value = "2026-01-30T00:00:00Z"

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            result = handler._check_file(mock_transport, "agents/chat/config.json", "bidirectional")

            assert isinstance(result, Conflict)
            assert "modified on both sides" in result.description
            assert result.remote_timestamp == "2026-01-30T00:00:00Z"


class TestDetectChanges:
    """Test detect_changes method."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory with structure."""
        data_dir = tmp_path / "data"
        (data_dir / "agents" / "chat").mkdir(parents=True)
        (data_dir / "agents" / "worker").mkdir(parents=True)
        (data_dir / "system").mkdir(parents=True)
        (data_dir / "topics" / "assets").mkdir(parents=True)
        (data_dir / "skills" / "core").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.list_remote_files.return_value = []
        transport.remote_directory_exists.return_value = False
        transport.remote_file_exists.return_value = False
        transport.get_remote_file_mtime.return_value = None
        return transport

    def test_detect_changes_empty(self, temp_data_dir, mock_transport):
        """detect_changes returns empty for no agents."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler

        # Remove agents directory
        import shutil
        shutil.rmtree(temp_data_dir / "agents")

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "push")

            # May have system config changes but no agent changes
            agent_changes = [c for c in changes if "agents/" in c.item_id]
            assert agent_changes == []

    def test_detect_changes_finds_local_agents(self, temp_data_dir, mock_transport):
        """detect_changes finds local agent files."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler

        # Create agent config
        config_path = temp_data_dir / "agents" / "chat" / "config.json"
        config_path.write_text('{"id": "chat"}')

        # Create agent identity
        identity_path = temp_data_dir / "agents" / "chat" / "identity.md"
        identity_path.write_text("# Chat Agent")

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "push")

            # Should find config.json and identity.md for push
            agent_changes = [c for c in changes if "agents/chat" in c.item_id]
            assert len(agent_changes) == 2
            assert all(c.type == "push" for c in agent_changes)


class TestApplyChanges:
    """Test apply_changes method."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "data"
        (data_dir / "agents" / "chat").mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.push_file.return_value = MagicMock(success=True)
        transport.fetch_file.return_value = MagicMock(success=True)
        transport.get_remote_file_mtime.return_value = None
        return transport

    def test_apply_changes_push(self, temp_data_dir, mock_transport):
        """apply_changes pushes files."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler
        from src.sync.sync import SyncChange

        # Create local file
        config_path = temp_data_dir / "agents" / "chat" / "config.json"
        config_path.write_text('{"id": "chat"}')

        change = SyncChange(
            type="push",
            handler="files",
            item_id="agents/chat/config.json",
            description="Push config",
        )

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            handler.apply_changes(mock_transport, "push", [change])

            assert change.applied is True
            mock_transport.push_file.assert_called_once()

    def test_apply_changes_pull(self, temp_data_dir, mock_transport):
        """apply_changes pulls files."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler
        from src.sync.sync import SyncChange

        change = SyncChange(
            type="pull",
            handler="files",
            item_id="agents/worker/config.json",
            description="Pull config",
        )

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            handler.apply_changes(mock_transport, "pull", [change])

            assert change.applied is True
            mock_transport.fetch_file.assert_called_once()

    def test_apply_changes_skips_other_handlers(self, temp_data_dir, mock_transport):
        """apply_changes skips changes for other handlers."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler
        from src.sync.sync import SyncChange

        change = SyncChange(
            type="push",
            handler="topics",  # Different handler
            item_id="topic-123",
            description="Push topic",
        )

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            handler.apply_changes(mock_transport, "push", [change])

            assert change.applied is False
            mock_transport.push_file.assert_not_called()

    def test_apply_changes_skips_conflicts(self, temp_data_dir, mock_transport):
        """apply_changes skips conflict changes."""
        from src.sync.handlers import files as files_module
        from src.sync.handlers.files import FilesSyncHandler
        from src.sync.sync import SyncChange

        change = SyncChange(
            type="conflict",
            handler="files",
            item_id="agents/chat/config.json",
            description="Conflict",
        )

        with patch.object(files_module, "DATA_DIR", temp_data_dir):
            handler = FilesSyncHandler()
            handler.apply_changes(mock_transport, "push", [change])

            assert change.applied is False
            mock_transport.push_file.assert_not_called()
