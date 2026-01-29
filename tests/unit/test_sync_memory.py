"""
Unit tests for sync memory handler.

Tests for src/sync/handlers/memory.py
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestMemorySyncHandler:
    """Test MemorySyncHandler class."""

    def test_handler_name(self):
        """Handler has correct name."""
        from src.sync.handlers.memory import MemorySyncHandler

        handler = MemorySyncHandler()

        assert handler.name == "memory"


class TestParseLongTermSections:
    """Test _parse_lt_sections method."""

    def test_parse_empty(self):
        """Parses empty content."""
        from src.sync.handlers.memory import MemorySyncHandler

        handler = MemorySyncHandler()
        result = handler._parse_lt_sections("")

        assert result == {}

    def test_parse_single_section(self):
        """Parses single section."""
        from src.sync.handlers.memory import MemorySyncHandler

        content = """# Memory

## 10:30 · Local Instance

Some content here.
More content.
"""
        handler = MemorySyncHandler()
        result = handler._parse_lt_sections(content)

        assert len(result) == 1
        assert "## 10:30 · Local Instance" in result
        assert "Some content here" in result["## 10:30 · Local Instance"]

    def test_parse_multiple_sections(self):
        """Parses multiple sections."""
        from src.sync.handlers.memory import MemorySyncHandler

        content = """# Memory

## 10:30 · Instance A

Content A.

## 11:45 · Instance B

Content B.
"""
        handler = MemorySyncHandler()
        result = handler._parse_lt_sections(content)

        assert len(result) == 2
        assert "## 10:30 · Instance A" in result
        assert "## 11:45 · Instance B" in result
        assert "Content A" in result["## 10:30 · Instance A"]
        assert "Content B" in result["## 11:45 · Instance B"]


class TestShortTermMemoryCheck:
    """Test short-term memory checking."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "data"
        agents_dir = data_dir / "agents" / "chat" / "memory"
        agents_dir.mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.remote_file_exists.return_value = False
        transport.get_remote_file_content.return_value = None
        transport.list_remote_files.return_value = []
        transport.remote_directory_exists.return_value = False
        return transport

    def test_check_short_term_empty(self, temp_data_dir, mock_transport):
        """No changes when both sides empty."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                changes, conflicts = handler._check_short_term(mock_transport, "chat", "push")

                assert changes == []
                assert conflicts == []

    def test_check_short_term_local_only(self, temp_data_dir, mock_transport):
        """Push change when local has entries remote doesn't."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Create local short-term memory
        memory_file = temp_data_dir / "agents" / "chat" / "memory" / "short-term.jsonl"
        memory_file.write_text('{"id": "mem-12345678", "type": "goal", "content": "Test"}\n')

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                changes, conflicts = handler._check_short_term(mock_transport, "chat", "push")

                assert len(changes) == 1
                assert changes[0].type == "push"
                assert "chat:short-term" in changes[0].item_id

    def test_check_short_term_remote_only(self, temp_data_dir, mock_transport):
        """Pull change when remote has entries local doesn't."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Mock remote has entries
        mock_transport.remote_file_exists.return_value = True
        mock_transport.get_remote_file_content.return_value = '{"id": "mem-87654321", "type": "goal", "content": "Remote"}\n'

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                changes, conflicts = handler._check_short_term(mock_transport, "chat", "pull")

                assert len(changes) == 1
                assert changes[0].type == "pull"

    def test_check_short_term_both_with_unique_entries(self, temp_data_dir, mock_transport):
        """Both push and pull when each side has unique entries."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Create local entry
        memory_file = temp_data_dir / "agents" / "chat" / "memory" / "short-term.jsonl"
        memory_file.write_text('{"id": "mem-local123", "type": "goal", "content": "Local"}\n')

        # Mock remote with different entry
        mock_transport.remote_file_exists.return_value = True
        mock_transport.get_remote_file_content.return_value = '{"id": "mem-remote456", "type": "idea", "content": "Remote"}\n'

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                changes, conflicts = handler._check_short_term(mock_transport, "chat", "bidirectional")

                assert len(changes) == 2
                types = {c.type for c in changes}
                assert "push" in types
                assert "pull" in types

    def test_check_short_term_same_id_different_content_conflict(self, temp_data_dir, mock_transport):
        """Conflict when same ID has different content and same date."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Create local entry
        memory_file = temp_data_dir / "agents" / "chat" / "memory" / "short-term.jsonl"
        memory_file.write_text('{"id": "mem-conflict1", "type": "goal", "content": "Local version", "date_mentioned": "2026-01-28"}\n')

        # Mock remote with same ID, same date, different content
        mock_transport.remote_file_exists.return_value = True
        mock_transport.get_remote_file_content.return_value = '{"id": "mem-conflict1", "type": "goal", "content": "Remote version", "date_mentioned": "2026-01-28"}\n'

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                changes, conflicts = handler._check_short_term(mock_transport, "chat", "bidirectional")

                assert len(conflicts) == 1
                assert "mem-conflict1" in conflicts[0].item_id


class TestLongTermMemoryCheck:
    """Test long-term memory checking."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "data"
        lt_dir = data_dir / "agents" / "chat" / "memory" / "long-term" / "2026"
        lt_dir.mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.remote_directory_exists.return_value = False
        transport.list_remote_files.return_value = []
        transport.get_remote_file_content.return_value = None
        return transport

    def test_check_long_term_local_only_file(self, temp_data_dir, mock_transport):
        """Push change for local-only file."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Create local long-term memory file
        lt_file = temp_data_dir / "agents" / "chat" / "memory" / "long-term" / "2026" / "2026-01-28.md"
        lt_file.write_text("# Memory\n\n## 10:30 · Local\n\nContent.\n")

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                changes, conflicts = handler._check_long_term(mock_transport, "chat", "push")

                assert len(changes) == 1
                assert changes[0].type == "push"
                assert "long-term" in changes[0].item_id

    def test_check_long_term_remote_only_file(self, temp_data_dir, mock_transport):
        """Pull change for remote-only file."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Mock remote has a file
        mock_transport.remote_directory_exists.return_value = True
        mock_transport.list_remote_files.side_effect = lambda path: (
            ["2026"] if path.endswith("long-term") else
            ["2026-01-27.md"] if "2026" in path else []
        )

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                changes, conflicts = handler._check_long_term(mock_transport, "chat", "pull")

                assert len(changes) == 1
                assert changes[0].type == "pull"

    def test_check_long_term_file_with_different_sections(self, temp_data_dir, mock_transport):
        """Changes for file with different sections on each side."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Create local file with one section
        lt_file = temp_data_dir / "agents" / "chat" / "memory" / "long-term" / "2026" / "2026-01-28.md"
        lt_file.write_text("# Memory\n\n## 10:30 · Local\n\nLocal content.\n")

        # Mock remote has same file with different section
        mock_transport.remote_directory_exists.return_value = True
        mock_transport.list_remote_files.side_effect = lambda path: (
            ["2026"] if path.endswith("long-term") else
            ["2026-01-28.md"] if "2026" in path else []
        )
        mock_transport.get_remote_file_content.return_value = "# Memory\n\n## 11:45 · Remote\n\nRemote content.\n"

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                changes, conflicts = handler._check_long_term(mock_transport, "chat", "bidirectional")

                # Should have both push and pull for different sections
                assert len(changes) == 2


class TestShortTermMemoryMerge:
    """Test short-term memory merge logic."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "data"
        memory_dir = data_dir / "agents" / "chat" / "memory"
        memory_dir.mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.get_remote_file_content.return_value = None
        transport.push_file.return_value = MagicMock(success=True)
        return transport

    def test_pull_short_term_merges_entries(self, temp_data_dir, mock_transport):
        """_pull_short_term merges entries from both sides."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Create local entry
        memory_file = temp_data_dir / "agents" / "chat" / "memory" / "short-term.jsonl"
        memory_file.write_text('{"id": "mem-local123", "type": "goal", "content": "Local"}\n')

        # Mock remote with different entry
        mock_transport.get_remote_file_content.return_value = '{"id": "mem-remote456", "type": "idea", "content": "Remote"}\n'

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                handler._pull_short_term(mock_transport, "chat")

                # Read merged file
                content = memory_file.read_text()
                lines = [l for l in content.strip().split("\n") if l]

                assert len(lines) == 2
                entries = [json.loads(l) for l in lines]
                ids = {e["id"] for e in entries}
                assert "mem-local123" in ids
                assert "mem-remote456" in ids

    def test_pull_short_term_remote_wins_for_newer(self, temp_data_dir, mock_transport):
        """_pull_short_term uses remote when remote is newer."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Create local entry
        memory_file = temp_data_dir / "agents" / "chat" / "memory" / "short-term.jsonl"
        memory_file.write_text('{"id": "mem-same123", "type": "goal", "content": "Local old", "date_mentioned": "2026-01-27"}\n')

        # Mock remote with same ID but newer date
        mock_transport.get_remote_file_content.return_value = '{"id": "mem-same123", "type": "goal", "content": "Remote new", "date_mentioned": "2026-01-28"}\n'

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                handler._pull_short_term(mock_transport, "chat")

                content = memory_file.read_text()
                entry = json.loads(content.strip())
                assert entry["content"] == "Remote new"


class TestLongTermMemoryMerge:
    """Test long-term memory merge logic."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "data"
        lt_dir = data_dir / "agents" / "chat" / "memory" / "long-term" / "2026"
        lt_dir.mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.get_remote_file_content.return_value = None
        transport.push_file.return_value = MagicMock(success=True)
        return transport

    def test_pull_long_term_merges_sections(self, temp_data_dir, mock_transport):
        """_pull_long_term_file merges sections from both sides."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Create local file with one section
        lt_file = temp_data_dir / "agents" / "chat" / "memory" / "long-term" / "2026" / "2026-01-28.md"
        lt_file.write_text("# Memory\n\n## 10:30 · Local\n\nLocal content.\n")

        # Mock remote with different section
        mock_transport.get_remote_file_content.return_value = "# Memory\n\n## 11:45 · Remote\n\nRemote content.\n"

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                handler._pull_long_term_file(mock_transport, "chat", "2026/2026-01-28.md")

                content = lt_file.read_text()
                assert "## 10:30 · Local" in content
                assert "## 11:45 · Remote" in content
                assert "Local content" in content
                assert "Remote content" in content

    def test_pull_long_term_preserves_existing_sections(self, temp_data_dir, mock_transport):
        """_pull_long_term_file doesn't duplicate existing sections."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler

        # Create local file with section
        lt_file = temp_data_dir / "agents" / "chat" / "memory" / "long-term" / "2026" / "2026-01-28.md"
        lt_file.write_text("# Memory\n\n## 10:30 · Shared\n\nShared content.\n")

        # Mock remote with same section
        mock_transport.get_remote_file_content.return_value = "# Memory\n\n## 10:30 · Shared\n\nShared content.\n"

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                handler._pull_long_term_file(mock_transport, "chat", "2026/2026-01-28.md")

                content = lt_file.read_text()
                # Should only have one instance of the section
                assert content.count("## 10:30 · Shared") == 1


class TestApplyChanges:
    """Test apply_changes method."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "data"
        memory_dir = data_dir / "agents" / "chat" / "memory"
        memory_dir.mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport."""
        transport = MagicMock()
        transport.get_remote_file_content.return_value = '{"id": "mem-test", "type": "goal", "content": "Test"}\n'
        transport.push_file.return_value = MagicMock(success=True)
        return transport

    def test_apply_changes_short_term_pull(self, temp_data_dir, mock_transport):
        """apply_changes handles short-term pull."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler
        from src.sync.sync import SyncChange

        change = SyncChange(
            type="pull",
            handler="memory",
            item_id="chat:short-term",
            description="Pull short-term memory",
        )

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                handler.apply_changes(mock_transport, "pull", [change])

                assert change.applied is True

    def test_apply_changes_skips_other_handlers(self, temp_data_dir, mock_transport):
        """apply_changes skips changes for other handlers."""
        from src.sync.handlers import memory as memory_module
        from src.sync.handlers.memory import MemorySyncHandler
        from src.sync.sync import SyncChange

        change = SyncChange(
            type="pull",
            handler="files",  # Different handler
            item_id="agents/chat/config.json",
            description="Pull file",
        )

        with patch.object(memory_module, "DATA_DIR", temp_data_dir):
            with patch.object(memory_module, "AGENTS_DIR", temp_data_dir / "agents"):
                handler = MemorySyncHandler()
                handler.apply_changes(mock_transport, "pull", [change])

                assert change.applied is False
