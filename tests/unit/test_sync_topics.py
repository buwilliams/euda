"""
Unit tests for sync topics handler.

Tests for src/sync/handlers/topics.py
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestTopicsSyncHandler:
    """Test TopicsSyncHandler class."""

    def test_handler_name(self):
        """Handler has correct name."""
        from src.sync.handlers.topics import TopicsSyncHandler

        handler = TopicsSyncHandler()

        assert handler.name == "topics"


class TestDetectChanges:
    """Test detect_changes method."""

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.run_remote_command.return_value = (False, "", "")
        transport.get_remote_file_content.return_value = None
        return transport

    @pytest.fixture
    def mock_export_topics(self):
        """Mock export_topics function."""
        return {
            "exported_at": "2026-01-28T10:00:00Z",
            "topics": [],
            "logs": [],
        }

    def test_detect_no_changes_empty(self, mock_transport, mock_export_topics):
        """No changes when both sides empty."""
        from src.sync.handlers.topics import TopicsSyncHandler

        with patch("src.core.data.topics.export_topics", return_value=mock_export_topics):
            handler = TopicsSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "bidirectional")

            assert changes == []
            assert conflicts == []

    def test_detect_local_only_topic_push(self, mock_transport):
        """Push change for local-only topic."""
        from src.sync.handlers.topics import TopicsSyncHandler

        local_data = {
            "exported_at": "2026-01-28T10:00:00Z",
            "topics": [
                {"id": "topic-local123", "name": "Local Topic", "updated_at": "2026-01-28T10:00:00Z"}
            ],
            "logs": [],
        }

        # Remote has no topics
        mock_transport.run_remote_command.return_value = (True, '{"topics": [], "logs": []}', "")

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            handler = TopicsSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "push")

            assert len(changes) == 1
            assert changes[0].type == "push"
            assert changes[0].item_id == "topic-local123"

    def test_detect_remote_only_topic_pull(self, mock_transport):
        """Pull change for remote-only topic."""
        from src.sync.handlers.topics import TopicsSyncHandler

        local_data = {
            "exported_at": "2026-01-28T10:00:00Z",
            "topics": [],
            "logs": [],
        }

        # Remote has a topic
        remote_data = {
            "topics": [
                {"id": "topic-remote456", "name": "Remote Topic", "updated_at": "2026-01-28T10:00:00Z"}
            ],
            "logs": [],
        }
        mock_transport.run_remote_command.return_value = (True, json.dumps(remote_data), "")

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            handler = TopicsSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "pull")

            assert len(changes) == 1
            assert changes[0].type == "pull"
            assert changes[0].item_id == "topic-remote456"

    def test_detect_tombstoned_topic_ignored(self, mock_transport):
        """Tombstoned topics are not re-pulled."""
        from src.sync.handlers.topics import TopicsSyncHandler

        local_data = {
            "exported_at": "2026-01-28T10:00:00Z",
            "topics": [],
            "logs": [],
        }
        remote_data = {
            "exported_at": "2026-01-28T10:00:00Z",
            "topics": [{"id": "topic-deleted", "name": "Old", "updated_at": "2026-01-28T10:00:00Z"}],
            "logs": [],
        }

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            with patch("src.core.data.deletions.get_deletions", return_value={
                "topics": {"topic-deleted": {"deleted_at": "2026-01-30T00:00:00Z"}},
                "memory": {},
            }):
                handler = TopicsSyncHandler()
                with patch.object(handler, "_fetch_remote_topics", return_value=remote_data):
                    with patch.object(handler, "_get_remote_deletions", return_value={}):
                        changes, conflicts = handler.detect_changes(mock_transport, "bidirectional")

        assert changes == []
        assert conflicts == []

    def test_detect_both_sides_same_no_change(self, mock_transport):
        """No change when topic unchanged on both sides."""
        from src.sync.handlers.topics import TopicsSyncHandler

        topic = {"id": "topic-same123", "name": "Same Topic", "updated_at": "2026-01-28T10:00:00Z"}
        local_data = {
            "exported_at": "2026-01-28T10:00:00Z",
            "topics": [topic],
            "logs": [],
        }
        remote_data = {
            "topics": [topic],
            "logs": [],
        }
        mock_transport.run_remote_command.return_value = (True, json.dumps(remote_data), "")

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            handler = TopicsSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "bidirectional")

            # No topic changes (maybe log changes if any)
            topic_changes = [c for c in changes if c.item_id.startswith("topic-")]
            assert topic_changes == []

    def test_detect_local_newer_bidirectional_push(self, mock_transport):
        """Push when local is newer in bidirectional mode."""
        from src.sync.handlers.topics import TopicsSyncHandler

        local_topic = {"id": "topic-123", "name": "Updated Local", "updated_at": "2026-01-28T11:00:00Z"}
        remote_topic = {"id": "topic-123", "name": "Old Remote", "updated_at": "2026-01-28T10:00:00Z"}

        local_data = {"exported_at": "...", "topics": [local_topic], "logs": []}
        remote_data = {"topics": [remote_topic], "logs": []}
        mock_transport.run_remote_command.return_value = (True, json.dumps(remote_data), "")

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            handler = TopicsSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "bidirectional")

            assert len(changes) == 1
            assert changes[0].type == "push"
            assert "newer" in changes[0].description.lower()

    def test_detect_remote_newer_bidirectional_pull(self, mock_transport):
        """Pull when remote is newer in bidirectional mode."""
        from src.sync.handlers.topics import TopicsSyncHandler

        local_topic = {"id": "topic-123", "name": "Old Local", "updated_at": "2026-01-28T10:00:00Z"}
        remote_topic = {"id": "topic-123", "name": "Updated Remote", "updated_at": "2026-01-28T11:00:00Z"}

        local_data = {"exported_at": "...", "topics": [local_topic], "logs": []}
        remote_data = {"topics": [remote_topic], "logs": []}
        mock_transport.run_remote_command.return_value = (True, json.dumps(remote_data), "")

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            handler = TopicsSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "bidirectional")

            assert len(changes) == 1
            assert changes[0].type == "pull"
            assert "newer" in changes[0].description.lower()

    def test_detect_log_entries_push(self, mock_transport):
        """Push change for local-only log entries."""
        from src.sync.handlers.topics import TopicsSyncHandler

        local_data = {
            "exported_at": "...",
            "topics": [],
            "logs": [
                {"topic_id": "topic-123", "timestamp": "2026-01-28T10:00:00Z", "agent": "chat", "action": "created"}
            ],
        }
        remote_data = {"topics": [], "logs": []}
        mock_transport.run_remote_command.return_value = (True, json.dumps(remote_data), "")

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            handler = TopicsSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "push")

            log_changes = [c for c in changes if c.item_id == "logs"]
            assert len(log_changes) == 1
            assert log_changes[0].type == "push"

    def test_detect_log_entries_pull(self, mock_transport):
        """Pull change for remote-only log entries."""
        from src.sync.handlers.topics import TopicsSyncHandler

        local_data = {"exported_at": "...", "topics": [], "logs": []}
        remote_data = {
            "topics": [],
            "logs": [
                {"topic_id": "topic-123", "timestamp": "2026-01-28T10:00:00Z", "agent": "worker", "action": "updated"}
            ],
        }
        mock_transport.run_remote_command.return_value = (True, json.dumps(remote_data), "")

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            handler = TopicsSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "pull")

            log_changes = [c for c in changes if c.item_id == "logs"]
            assert len(log_changes) == 1
            assert log_changes[0].type == "pull"

    def test_detect_remote_not_available_push_all(self, mock_transport):
        """Push all when remote has no topics export."""
        from src.sync.handlers.topics import TopicsSyncHandler

        local_data = {
            "exported_at": "...",
            "topics": [
                {"id": "topic-1", "name": "Topic 1", "updated_at": "..."},
                {"id": "topic-2", "name": "Topic 2", "updated_at": "..."},
            ],
            "logs": [],
        }
        # Remote command fails (no topics export available)
        mock_transport.run_remote_command.return_value = (False, "", "error")

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            handler = TopicsSyncHandler()
            changes, conflicts = handler.detect_changes(mock_transport, "push")

            assert len(changes) == 1
            assert changes[0].item_id == "all"
            assert "2 topics" in changes[0].description


class TestApplyChanges:
    """Test apply_changes method."""

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.run_remote_command.return_value = (True, '{"imported": 1}', "")
        transport.host = "user@server"
        transport.remote_path = "/opt/euno"
        return transport

    def test_apply_pull_changes(self, mock_transport):
        """apply_changes imports topics on pull."""
        from src.sync.handlers.topics import TopicsSyncHandler
        from src.sync.sync import SyncChange

        remote_data = {
            "topics": [{"id": "topic-remote", "name": "Remote Topic"}],
            "logs": [],
        }
        mock_transport.run_remote_command.return_value = (True, json.dumps(remote_data), "")

        change = SyncChange(
            type="pull",
            handler="topics",
            item_id="topic-remote",
            description="Pull topic",
        )

        with patch("src.core.data.topics.export_topics", return_value={"topics": [], "logs": []}):
            with patch("src.core.data.topics.import_topics", return_value={"imported": 1}) as mock_import:
                handler = TopicsSyncHandler()
                handler.apply_changes(mock_transport, "pull", [change])

                assert change.applied is True
                mock_import.assert_called_once()

    def test_apply_push_changes(self, mock_transport):
        """apply_changes exports and pushes topics."""
        from src.sync.handlers.topics import TopicsSyncHandler
        from src.sync.sync import SyncChange

        local_data = {
            "topics": [{"id": "topic-local", "name": "Local Topic"}],
            "logs": [],
        }

        change = SyncChange(
            type="push",
            handler="topics",
            item_id="topic-local",
            description="Push topic",
        )

        with patch("src.core.data.topics.export_topics", return_value=local_data):
            with patch("subprocess.run"):
                handler = TopicsSyncHandler()
                handler.apply_changes(mock_transport, "push", [change])

                assert change.applied is True

    def test_apply_skips_other_handlers(self, mock_transport):
        """apply_changes skips changes for other handlers."""
        from src.sync.handlers.topics import TopicsSyncHandler
        from src.sync.sync import SyncChange

        change = SyncChange(
            type="push",
            handler="files",  # Different handler
            item_id="config.json",
            description="Push file",
        )

        with patch("src.core.data.topics.export_topics", return_value={"topics": [], "logs": []}):
            handler = TopicsSyncHandler()
            handler.apply_changes(mock_transport, "push", [change])

            assert change.applied is False

    def test_apply_skips_conflicts(self, mock_transport):
        """apply_changes skips conflict changes."""
        from src.sync.handlers.topics import TopicsSyncHandler
        from src.sync.sync import SyncChange

        change = SyncChange(
            type="conflict",
            handler="topics",
            item_id="topic-conflict",
            description="Conflict",
        )

        with patch("src.core.data.topics.export_topics", return_value={"topics": [], "logs": []}):
            handler = TopicsSyncHandler()
            handler.apply_changes(mock_transport, "push", [change])

            assert change.applied is False


class TestFetchRemoteTopics:
    """Test _fetch_remote_topics method."""

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.remote_path = "/opt/euno"
        return transport

    def test_fetch_success(self, mock_transport):
        """Successfully fetches remote topics."""
        from src.sync.handlers.topics import TopicsSyncHandler

        remote_data = {"topics": [{"id": "topic-1"}], "logs": []}
        mock_transport.run_remote_command.return_value = (True, json.dumps(remote_data), "")

        handler = TopicsSyncHandler()
        result = handler._fetch_remote_topics(mock_transport)

        assert result is not None
        assert len(result["topics"]) == 1

    def test_fetch_failure_returns_none(self, mock_transport):
        """Returns None when fetch fails."""
        from src.sync.handlers.topics import TopicsSyncHandler

        mock_transport.run_remote_command.return_value = (False, "", "Connection refused")

        handler = TopicsSyncHandler()
        result = handler._fetch_remote_topics(mock_transport)

        assert result is None

    def test_fetch_invalid_json_returns_none(self, mock_transport):
        """Returns None when response is invalid JSON."""
        from src.sync.handlers.topics import TopicsSyncHandler

        mock_transport.run_remote_command.return_value = (True, "not valid json", "")

        handler = TopicsSyncHandler()
        result = handler._fetch_remote_topics(mock_transport)

        assert result is None

    def test_fetch_empty_response_returns_none(self, mock_transport):
        """Returns None when response is empty."""
        from src.sync.handlers.topics import TopicsSyncHandler

        mock_transport.run_remote_command.return_value = (True, "", "")

        handler = TopicsSyncHandler()
        result = handler._fetch_remote_topics(mock_transport)

        assert result is None
