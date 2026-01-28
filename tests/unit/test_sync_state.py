"""
Unit tests for sync state module.

Tests for src/sync/state.py
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


class TestSyncState:
    """Test SyncState dataclass."""

    def test_sync_state_generates_instance_id(self):
        """SyncState generates instance ID if not provided."""
        from src.sync.state import SyncState

        state = SyncState()

        assert state.instance_id.startswith("euno-")
        assert len(state.instance_id) == 17  # "euno-" (5) + 12 hex chars

    def test_sync_state_preserves_instance_id(self):
        """SyncState preserves provided instance ID."""
        from src.sync.state import SyncState

        state = SyncState(instance_id="euno-custom123456")

        assert state.instance_id == "euno-custom123456"

    def test_sync_state_to_dict_minimal(self):
        """SyncState.to_dict with minimal fields."""
        from src.sync.state import SyncState

        state = SyncState(instance_id="euno-test123")
        result = state.to_dict()

        assert result["version"] == 1
        assert result["instance_id"] == "euno-test123"
        assert "last_sync" not in result
        assert "remote" not in result

    def test_sync_state_to_dict_full(self):
        """SyncState.to_dict with all fields."""
        from src.sync.state import SyncState, LastSync, RemoteConfig

        state = SyncState(
            instance_id="euno-test123",
            last_sync=LastSync(
                timestamp="2026-01-28T10:00:00Z",
                remote_instance_id="euno-remote456",
                success=True,
                direction="push",
                changes_pushed=5,
                changes_pulled=0,
            ),
            remote=RemoteConfig(host="user@server.com", path="/opt/euno"),
        )
        result = state.to_dict()

        assert result["last_sync"]["timestamp"] == "2026-01-28T10:00:00Z"
        assert result["last_sync"]["changes_pushed"] == 5
        assert result["remote"]["host"] == "user@server.com"

    def test_sync_state_from_dict(self):
        """SyncState.from_dict creates correct state."""
        from src.sync.state import SyncState

        data = {
            "version": 1,
            "instance_id": "euno-loaded123",
            "last_sync": {
                "timestamp": "2026-01-28T10:00:00Z",
                "remote_instance_id": "euno-remote456",
                "success": True,
                "direction": "bidirectional",
                "changes_pushed": 3,
                "changes_pulled": 2,
            },
            "remote": {"host": "user@server.com", "path": "/opt/euno"},
        }
        state = SyncState.from_dict(data)

        assert state.instance_id == "euno-loaded123"
        assert state.last_sync.success is True
        assert state.last_sync.changes_pushed == 3
        assert state.remote.host == "user@server.com"

    def test_sync_state_from_dict_minimal(self):
        """SyncState.from_dict with minimal data."""
        from src.sync.state import SyncState

        data = {"version": 1}
        state = SyncState.from_dict(data)

        # Should generate instance ID since not provided
        assert state.instance_id.startswith("euno-")
        assert state.last_sync is None
        assert state.remote is None


class TestStatePersistence:
    """Test state persistence functions."""

    @pytest.fixture
    def temp_sync_dir(self, tmp_path):
        """Create a temporary sync directory."""
        sync_dir = tmp_path / "data" / "system" / "sync"
        sync_dir.mkdir(parents=True)
        return sync_dir

    def test_get_sync_state_creates_new(self, temp_sync_dir):
        """get_sync_state creates new state if none exists."""
        from src.sync import state as state_module

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir):
            with patch.object(state_module, "STATE_PATH", temp_sync_dir / "state.json"):
                result = state_module.get_sync_state()

                assert result.instance_id.startswith("euno-")
                assert (temp_sync_dir / "state.json").exists()

    def test_get_sync_state_loads_existing(self, temp_sync_dir):
        """get_sync_state loads existing state."""
        from src.sync import state as state_module

        state_path = temp_sync_dir / "state.json"
        state_path.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-existing123",
        }))

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir):
            with patch.object(state_module, "STATE_PATH", state_path):
                result = state_module.get_sync_state()

                assert result.instance_id == "euno-existing123"

    def test_save_sync_state(self, temp_sync_dir):
        """save_sync_state writes state to disk."""
        from src.sync import state as state_module
        from src.sync.state import SyncState

        state_path = temp_sync_dir / "state.json"

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir):
            with patch.object(state_module, "STATE_PATH", state_path):
                state = SyncState(instance_id="euno-saved123")
                state_module.save_sync_state(state)

                loaded = json.loads(state_path.read_text())
                assert loaded["instance_id"] == "euno-saved123"

    def test_get_instance_id(self, temp_sync_dir):
        """get_instance_id returns the instance ID."""
        from src.sync import state as state_module

        state_path = temp_sync_dir / "state.json"
        state_path.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-myinstance",
        }))

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir):
            with patch.object(state_module, "STATE_PATH", state_path):
                result = state_module.get_instance_id()

                assert result == "euno-myinstance"


class TestInitSync:
    """Test sync initialization."""

    @pytest.fixture
    def temp_sync_dir(self, tmp_path):
        """Create a temporary sync directory."""
        sync_dir = tmp_path / "data" / "system" / "sync"
        sync_dir.mkdir(parents=True)
        return sync_dir

    def test_init_sync_sets_remote(self, temp_sync_dir):
        """init_sync configures remote server."""
        from src.sync import state as state_module

        state_path = temp_sync_dir / "state.json"
        state_path.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
        }))

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir):
            with patch.object(state_module, "STATE_PATH", state_path):
                result = state_module.init_sync("user@server.com")

                assert result.remote is not None
                assert result.remote.host == "user@server.com"
                assert result.remote.path == "/opt/euno"

    def test_init_sync_custom_path(self, temp_sync_dir):
        """init_sync with custom remote path."""
        from src.sync import state as state_module

        state_path = temp_sync_dir / "state.json"
        state_path.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
        }))

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir):
            with patch.object(state_module, "STATE_PATH", state_path):
                result = state_module.init_sync("root@server.com", "/home/euno/app")

                assert result.remote.path == "/home/euno/app"


class TestRecordSync:
    """Test sync recording."""

    @pytest.fixture
    def temp_sync_dir(self, tmp_path):
        """Create a temporary sync directory."""
        sync_dir = tmp_path / "data" / "system" / "sync"
        sync_dir.mkdir(parents=True)
        return sync_dir

    def test_record_sync_creates_last_sync(self, temp_sync_dir):
        """record_sync creates last_sync record."""
        from src.sync import state as state_module

        state_path = temp_sync_dir / "state.json"
        state_path.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
        }))

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir):
            with patch.object(state_module, "STATE_PATH", state_path):
                result = state_module.record_sync(
                    remote_instance_id="euno-remote456",
                    success=True,
                    direction="push",
                    changes_pushed=5,
                    changes_pulled=0,
                )

                assert result.last_sync is not None
                assert result.last_sync.remote_instance_id == "euno-remote456"
                assert result.last_sync.success is True
                assert result.last_sync.changes_pushed == 5

    def test_record_sync_persists(self, temp_sync_dir):
        """record_sync saves to disk."""
        from src.sync import state as state_module

        state_path = temp_sync_dir / "state.json"
        state_path.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
        }))

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir):
            with patch.object(state_module, "STATE_PATH", state_path):
                state_module.record_sync(
                    remote_instance_id="euno-remote456",
                    success=True,
                )

                loaded = json.loads(state_path.read_text())
                assert loaded["last_sync"]["remote_instance_id"] == "euno-remote456"


class TestClearRemote:
    """Test clearing remote configuration."""

    @pytest.fixture
    def temp_sync_dir(self, tmp_path):
        """Create a temporary sync directory."""
        sync_dir = tmp_path / "data" / "system" / "sync"
        sync_dir.mkdir(parents=True)
        return sync_dir

    def test_clear_remote_removes_config(self, temp_sync_dir):
        """clear_remote removes remote configuration."""
        from src.sync import state as state_module

        state_path = temp_sync_dir / "state.json"
        state_path.write_text(json.dumps({
            "version": 1,
            "instance_id": "euno-local123",
            "remote": {"host": "user@server.com", "path": "/opt/euno"},
        }))

        with patch.object(state_module, "SYNC_DIR", temp_sync_dir):
            with patch.object(state_module, "STATE_PATH", state_path):
                result = state_module.clear_remote()

                assert result.remote is None

                loaded = json.loads(state_path.read_text())
                assert "remote" not in loaded
