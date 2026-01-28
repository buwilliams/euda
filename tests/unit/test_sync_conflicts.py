"""
Unit tests for sync conflicts module.

Tests for src/sync/conflicts.py
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


class TestConflictCreation:
    """Test conflict creation."""

    @pytest.fixture
    def temp_conflicts_dir(self, tmp_path):
        """Create a temporary conflicts directory."""
        conflicts_dir = tmp_path / "data" / "system" / "sync" / "conflicts"
        conflicts_dir.mkdir(parents=True)
        return conflicts_dir

    def test_create_conflict_basic(self, temp_conflicts_dir):
        """Create a basic conflict."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            conflict = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="agents/chat/config.json",
                description="File modified on both sides",
                local={"key": "local_value"},
                remote={"key": "remote_value"},
            )

            assert conflict.id.startswith("conflict-")
            assert conflict.type == ConflictType.FILE
            assert conflict.item_id == "agents/chat/config.json"
            assert conflict.resolution is None

    def test_create_conflict_saves_file(self, temp_conflicts_dir):
        """create_conflict saves conflict to file."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            conflict = conflicts_module.create_conflict(
                conflict_type=ConflictType.TOPICS,
                item_id="topic-12345678",
                description="Topic modified on both sides",
                local={"name": "Local Name"},
                remote={"name": "Remote Name"},
            )

            # Check file was created
            files = list(temp_conflicts_dir.glob("*.json"))
            assert len(files) == 1

            # Check file content
            content = json.loads(files[0].read_text())
            assert content["id"] == conflict.id
            assert content["type"] == "topics"

    def test_create_conflict_with_timestamps(self, temp_conflicts_dir):
        """Create conflict with timestamps."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            conflict = conflicts_module.create_conflict(
                conflict_type=ConflictType.AGENT_CONFIG,
                item_id="agents/worker/config.json",
                description="Agent config conflict",
                local={"state": "enabled"},
                remote={"state": "disabled"},
                local_timestamp="2026-01-28T10:00:00Z",
                remote_timestamp="2026-01-28T09:00:00Z",
            )

            assert conflict.local_timestamp == "2026-01-28T10:00:00Z"
            assert conflict.remote_timestamp == "2026-01-28T09:00:00Z"


class TestConflictListing:
    """Test conflict listing."""

    @pytest.fixture
    def temp_conflicts_dir(self, tmp_path):
        """Create a temporary conflicts directory with conflicts."""
        conflicts_dir = tmp_path / "data" / "system" / "sync" / "conflicts"
        conflicts_dir.mkdir(parents=True)
        return conflicts_dir

    def test_list_conflicts_empty(self, temp_conflicts_dir):
        """list_conflicts returns empty list when no conflicts."""
        from src.sync import conflicts as conflicts_module

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            result = conflicts_module.list_conflicts()

            assert result == []

    def test_list_conflicts_unresolved(self, temp_conflicts_dir):
        """list_conflicts returns unresolved conflicts by default."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            # Create two conflicts
            c1 = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="file1.txt",
                description="Conflict 1",
                local="local1",
                remote="remote1",
            )
            c2 = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="file2.txt",
                description="Conflict 2",
                local="local2",
                remote="remote2",
            )

            result = conflicts_module.list_conflicts()

            assert len(result) == 2
            ids = {c.id for c in result}
            assert c1.id in ids
            assert c2.id in ids

    def test_list_conflicts_excludes_resolved(self, temp_conflicts_dir):
        """list_conflicts excludes resolved conflicts by default."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType, Resolution

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            c1 = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="file1.txt",
                description="Conflict 1",
                local="local1",
                remote="remote1",
            )
            c2 = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="file2.txt",
                description="Conflict 2",
                local="local2",
                remote="remote2",
            )

            # Resolve one conflict
            conflicts_module.resolve_conflict(c1.id, Resolution.KEEP_LOCAL)

            result = conflicts_module.list_conflicts(resolved=False)

            assert len(result) == 1
            assert result[0].id == c2.id

    def test_list_conflicts_includes_resolved(self, temp_conflicts_dir):
        """list_conflicts includes resolved when resolved=True."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType, Resolution

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            c1 = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="file1.txt",
                description="Conflict 1",
                local="local1",
                remote="remote1",
            )
            conflicts_module.resolve_conflict(c1.id, Resolution.KEEP_LOCAL)

            result = conflicts_module.list_conflicts(resolved=True)

            assert len(result) == 1
            assert result[0].resolution == Resolution.KEEP_LOCAL


class TestConflictRetrieval:
    """Test getting individual conflicts."""

    @pytest.fixture
    def temp_conflicts_dir(self, tmp_path):
        """Create a temporary conflicts directory."""
        conflicts_dir = tmp_path / "data" / "system" / "sync" / "conflicts"
        conflicts_dir.mkdir(parents=True)
        return conflicts_dir

    def test_get_conflict_exists(self, temp_conflicts_dir):
        """get_conflict returns conflict by ID."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            created = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="test.txt",
                description="Test conflict",
                local="local",
                remote="remote",
            )

            result = conflicts_module.get_conflict(created.id)

            assert result is not None
            assert result.id == created.id
            assert result.item_id == "test.txt"

    def test_get_conflict_not_found(self, temp_conflicts_dir):
        """get_conflict returns None for unknown ID."""
        from src.sync import conflicts as conflicts_module

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            result = conflicts_module.get_conflict("conflict-nonexistent")

            assert result is None


class TestConflictResolution:
    """Test conflict resolution."""

    @pytest.fixture
    def temp_conflicts_dir(self, tmp_path):
        """Create a temporary conflicts directory."""
        conflicts_dir = tmp_path / "data" / "system" / "sync" / "conflicts"
        conflicts_dir.mkdir(parents=True)
        return conflicts_dir

    def test_resolve_conflict_keep_local(self, temp_conflicts_dir):
        """resolve_conflict with KEEP_LOCAL."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType, Resolution

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            created = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="test.txt",
                description="Test",
                local="local",
                remote="remote",
            )

            result = conflicts_module.resolve_conflict(created.id, Resolution.KEEP_LOCAL)

            assert result is not None
            assert result.resolution == Resolution.KEEP_LOCAL
            assert result.resolved_at is not None

    def test_resolve_conflict_persists(self, temp_conflicts_dir):
        """resolve_conflict saves to disk."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType, Resolution

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            created = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="test.txt",
                description="Test",
                local="local",
                remote="remote",
            )

            conflicts_module.resolve_conflict(created.id, Resolution.KEEP_REMOTE)

            # Reload from disk
            loaded = conflicts_module.get_conflict(created.id)
            assert loaded.resolution == Resolution.KEEP_REMOTE

    def test_resolve_conflict_not_found(self, temp_conflicts_dir):
        """resolve_conflict returns None for unknown ID."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import Resolution

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            result = conflicts_module.resolve_conflict("conflict-fake", Resolution.KEEP_LOCAL)

            assert result is None


class TestConflictDeletion:
    """Test conflict deletion."""

    @pytest.fixture
    def temp_conflicts_dir(self, tmp_path):
        """Create a temporary conflicts directory."""
        conflicts_dir = tmp_path / "data" / "system" / "sync" / "conflicts"
        conflicts_dir.mkdir(parents=True)
        return conflicts_dir

    def test_delete_conflict(self, temp_conflicts_dir):
        """delete_conflict removes conflict file."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            created = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="test.txt",
                description="Test",
                local="local",
                remote="remote",
            )

            result = conflicts_module.delete_conflict(created.id)

            assert result is True
            assert conflicts_module.get_conflict(created.id) is None

    def test_delete_conflict_not_found(self, temp_conflicts_dir):
        """delete_conflict returns False for unknown ID."""
        from src.sync import conflicts as conflicts_module

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            result = conflicts_module.delete_conflict("conflict-nonexistent")

            assert result is False

    def test_clear_resolved_conflicts(self, temp_conflicts_dir):
        """clear_resolved_conflicts removes only resolved conflicts."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType, Resolution

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            c1 = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="file1.txt",
                description="Conflict 1",
                local="local1",
                remote="remote1",
            )
            c2 = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="file2.txt",
                description="Conflict 2",
                local="local2",
                remote="remote2",
            )

            conflicts_module.resolve_conflict(c1.id, Resolution.KEEP_LOCAL)

            deleted = conflicts_module.clear_resolved_conflicts()

            assert deleted == 1
            assert conflicts_module.get_conflict(c1.id) is None
            assert conflicts_module.get_conflict(c2.id) is not None


class TestHasUnresolvedConflicts:
    """Test has_unresolved_conflicts function."""

    @pytest.fixture
    def temp_conflicts_dir(self, tmp_path):
        """Create a temporary conflicts directory."""
        conflicts_dir = tmp_path / "data" / "system" / "sync" / "conflicts"
        conflicts_dir.mkdir(parents=True)
        return conflicts_dir

    def test_has_unresolved_true(self, temp_conflicts_dir):
        """has_unresolved_conflicts returns True when conflicts exist."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="test.txt",
                description="Test",
                local="local",
                remote="remote",
            )

            assert conflicts_module.has_unresolved_conflicts() is True

    def test_has_unresolved_false_empty(self, temp_conflicts_dir):
        """has_unresolved_conflicts returns False when no conflicts."""
        from src.sync import conflicts as conflicts_module

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            assert conflicts_module.has_unresolved_conflicts() is False

    def test_has_unresolved_false_all_resolved(self, temp_conflicts_dir):
        """has_unresolved_conflicts returns False when all resolved."""
        from src.sync import conflicts as conflicts_module
        from src.sync.conflicts import ConflictType, Resolution

        with patch.object(conflicts_module, "CONFLICTS_DIR", temp_conflicts_dir):
            created = conflicts_module.create_conflict(
                conflict_type=ConflictType.FILE,
                item_id="test.txt",
                description="Test",
                local="local",
                remote="remote",
            )
            conflicts_module.resolve_conflict(created.id, Resolution.KEEP_LOCAL)

            assert conflicts_module.has_unresolved_conflicts() is False


class TestGetResolvedData:
    """Test get_resolved_data function."""

    def test_keep_local(self):
        """get_resolved_data returns local for KEEP_LOCAL."""
        from src.sync.conflicts import Conflict, ConflictType, Resolution, get_resolved_data

        conflict = Conflict(
            id="conflict-test",
            type=ConflictType.FILE,
            detected_at="2026-01-28T10:00:00Z",
            item_id="test.txt",
            description="Test",
            local={"key": "local"},
            remote={"key": "remote"},
            resolution=Resolution.KEEP_LOCAL,
        )

        result = get_resolved_data(conflict)

        assert result == {"key": "local"}

    def test_keep_remote(self):
        """get_resolved_data returns remote for KEEP_REMOTE."""
        from src.sync.conflicts import Conflict, ConflictType, Resolution, get_resolved_data

        conflict = Conflict(
            id="conflict-test",
            type=ConflictType.FILE,
            detected_at="2026-01-28T10:00:00Z",
            item_id="test.txt",
            description="Test",
            local={"key": "local"},
            remote={"key": "remote"},
            resolution=Resolution.KEEP_REMOTE,
        )

        result = get_resolved_data(conflict)

        assert result == {"key": "remote"}

    def test_keep_newest_local(self):
        """get_resolved_data returns local when local is newer."""
        from src.sync.conflicts import Conflict, ConflictType, Resolution, get_resolved_data

        conflict = Conflict(
            id="conflict-test",
            type=ConflictType.FILE,
            detected_at="2026-01-28T10:00:00Z",
            item_id="test.txt",
            description="Test",
            local={"key": "local"},
            remote={"key": "remote"},
            local_timestamp="2026-01-28T11:00:00Z",
            remote_timestamp="2026-01-28T10:00:00Z",
            resolution=Resolution.KEEP_NEWEST,
        )

        result = get_resolved_data(conflict)

        assert result == {"key": "local"}

    def test_keep_newest_remote(self):
        """get_resolved_data returns remote when remote is newer."""
        from src.sync.conflicts import Conflict, ConflictType, Resolution, get_resolved_data

        conflict = Conflict(
            id="conflict-test",
            type=ConflictType.FILE,
            detected_at="2026-01-28T10:00:00Z",
            item_id="test.txt",
            description="Test",
            local={"key": "local"},
            remote={"key": "remote"},
            local_timestamp="2026-01-28T09:00:00Z",
            remote_timestamp="2026-01-28T10:00:00Z",
            resolution=Resolution.KEEP_NEWEST,
        )

        result = get_resolved_data(conflict)

        assert result == {"key": "remote"}

    def test_unresolved(self):
        """get_resolved_data returns None for unresolved conflict."""
        from src.sync.conflicts import Conflict, ConflictType, get_resolved_data

        conflict = Conflict(
            id="conflict-test",
            type=ConflictType.FILE,
            detected_at="2026-01-28T10:00:00Z",
            item_id="test.txt",
            description="Test",
            local={"key": "local"},
            remote={"key": "remote"},
            resolution=None,
        )

        result = get_resolved_data(conflict)

        assert result is None


class TestDeepMerge:
    """Test deep_merge function."""

    def test_merge_flat(self):
        """deep_merge merges flat dictionaries."""
        from src.sync.conflicts import deep_merge

        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested(self):
        """deep_merge merges nested dictionaries."""
        from src.sync.conflicts import deep_merge

        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 20, "z": 30}}

        result = deep_merge(base, override)

        assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3}

    def test_merge_deep_nested(self):
        """deep_merge handles deeply nested structures."""
        from src.sync.conflicts import deep_merge

        base = {"a": {"b": {"c": 1}}}
        override = {"a": {"b": {"d": 2}}}

        result = deep_merge(base, override)

        assert result == {"a": {"b": {"c": 1, "d": 2}}}

    def test_merge_non_dict_override(self):
        """deep_merge replaces non-dict values."""
        from src.sync.conflicts import deep_merge

        base = {"a": {"x": 1}}
        override = {"a": "replaced"}

        result = deep_merge(base, override)

        assert result == {"a": "replaced"}
