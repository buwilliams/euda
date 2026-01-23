"""
Unit tests for memory module.

Tests for src/tools/data/memory.py
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch


class TestShortTermMemory:
    """Test short-term memory operations."""

    def test_add_memory(self, patch_data_dir):
        """Add a memory item."""
        from src.tools.data.memory import add_memory

        # Create agent directory
        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        entry = add_memory(
            short_description="Remember this",
            type="idea",
            agent_id="test-agent"
        )

        assert entry["id"].startswith("mem-")
        assert entry["short_description"] == "Remember this"
        assert entry["type"] == "idea"
        assert entry["date_mentioned"] == datetime.now().strftime('%Y-%m-%d')

    def test_add_memory_with_expected_date(self, patch_data_dir):
        """Add a memory item with expected date."""
        from src.tools.data.memory import add_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        entry = add_memory(
            short_description="Future event",
            type="goal",
            date_expected="2024-12-31",
            agent_id="test-agent"
        )

        assert entry["date_expected"] == "2024-12-31"

    def test_list_memory_returns_valid_only(self, patch_data_dir):
        """list_memory returns only valid entries."""
        from src.tools.data.memory import add_memory, list_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Add valid entry
        add_memory(
            short_description="Valid entry",
            type="idea",
            agent_id="test-agent"
        )

        entries = list_memory(agent_id="test-agent")

        assert len(entries) == 1
        assert entries[0]["short_description"] == "Valid entry"

    def test_remove_memory(self, patch_data_dir):
        """Remove a memory item by ID."""
        from src.tools.data.memory import add_memory, remove_memory, list_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        entry = add_memory(
            short_description="Remove me",
            type="idea",
            agent_id="test-agent"
        )

        result = remove_memory(entry["id"], agent_id="test-agent")
        assert result["removed"] == entry["id"]

        entries = list_memory(agent_id="test-agent")
        assert len(entries) == 0

    def test_remove_memory_not_found(self, patch_data_dir):
        """Remove non-existent memory returns error."""
        from src.tools.data.memory import remove_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        result = remove_memory("mem-nonexistent", agent_id="test-agent")
        assert "error" in result


class TestLongTermMemory:
    """Test long-term memory operations."""

    def test_write_long_term_memory(self, patch_data_dir):
        """Write an entry to long-term memory."""
        from src.tools.data.memory import write_long_term_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        result = write_long_term_memory(
            content="Important memory",
            agent_id="test-agent",
            source="Test"
        )

        assert result["status"] == "added"
        assert result["agent_id"] == "test-agent"

        # Verify file was created
        today = datetime.now().strftime("%Y-%m-%d")
        year = datetime.now().strftime("%Y")
        memory_file = patch_data_dir / "agents" / "test-agent" / "memory" / "long-term" / year / f"{today}.md"
        assert memory_file.exists()

        content = memory_file.read_text()
        assert "Important memory" in content
        assert "Test" in content  # Source

    def test_write_long_term_memory_appends(self, patch_data_dir):
        """Multiple writes to same day append to file."""
        from src.tools.data.memory import write_long_term_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        write_long_term_memory(content="First entry", agent_id="test-agent", source="Test")
        write_long_term_memory(content="Second entry", agent_id="test-agent", source="Test")

        today = datetime.now().strftime("%Y-%m-%d")
        year = datetime.now().strftime("%Y")
        memory_file = patch_data_dir / "agents" / "test-agent" / "memory" / "long-term" / year / f"{today}.md"

        content = memory_file.read_text()
        assert "First entry" in content
        assert "Second entry" in content


class TestMemoryGraduation:
    """Test graduating short-term to long-term memory."""

    def test_graduate_memory(self, patch_data_dir):
        """Graduate a short-term memory to long-term."""
        from src.tools.data.memory import add_memory, graduate_memory, list_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Add short-term memory
        entry = add_memory(
            short_description="Graduate me",
            type="learning",
            agent_id="test-agent"
        )

        # Graduate it
        result = graduate_memory(entry["id"], reason="Important insight", agent_id="test-agent")

        assert result["graduated"] == entry["id"]
        assert result["type"] == "learning"

        # Should be removed from short-term
        entries = list_memory(agent_id="test-agent")
        assert len(entries) == 0

    def test_graduate_memory_not_found(self, patch_data_dir):
        """Graduate non-existent memory returns error."""
        from src.tools.data.memory import graduate_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        result = graduate_memory("mem-nonexistent", agent_id="test-agent")
        assert "error" in result


class TestMemoryPersistence:
    """Test memory persistence to disk."""

    def test_short_term_persistence(self, patch_data_dir):
        """Short-term memory persists to JSONL file."""
        from src.tools.data.memory import add_memory, _get_short_term_path

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        add_memory(
            short_description="Persist me",
            type="idea",
            agent_id="test-agent"
        )

        path = _get_short_term_path("test-agent")
        assert path.exists()

        # Verify JSONL format
        with open(path) as f:
            line = f.readline()
            entry = json.loads(line)
            assert entry["short_description"] == "Persist me"

    def test_long_term_uses_year_directory(self, patch_data_dir):
        """Long-term memory uses year-based directory structure."""
        from src.tools.data.memory import write_long_term_memory, _get_long_term_dir

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Write for a specific date in 2023
        write_long_term_memory(
            content="Old memory",
            date="2023-06-15",
            agent_id="test-agent"
        )

        # Verify it's in the 2023 directory
        memory_file = patch_data_dir / "agents" / "test-agent" / "memory" / "long-term" / "2023" / "2023-06-15.md"
        assert memory_file.exists()


class TestMemoryForPrompt:
    """Test memory formatting for system prompts."""

    def test_get_memory_for_prompt_empty(self, patch_data_dir):
        """Empty memory returns empty string."""
        from src.tools.data.memory import get_memory_for_prompt

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        result = get_memory_for_prompt(agent_id="test-agent")
        assert result == ""

    def test_get_memory_for_prompt_formatted(self, patch_data_dir):
        """Memory is formatted with headers and types."""
        from src.tools.data.memory import add_memory, get_memory_for_prompt

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        add_memory(
            short_description="Meeting with John",
            type="person",
            agent_id="test-agent"
        )
        add_memory(
            short_description="Finish project",
            type="goal",
            agent_id="test-agent"
        )

        result = get_memory_for_prompt(agent_id="test-agent")

        assert "## Memory" in result
        assert "**person**" in result
        assert "**goal**" in result
        assert "Meeting with John" in result
        assert "Finish project" in result


class TestMemoryDirectoryCreation:
    """Test memory directory auto-creation."""

    def test_ensure_memory_dirs(self, patch_data_dir):
        """Memory directories are created automatically."""
        from src.tools.data.memory import _ensure_memory_dirs

        _ensure_memory_dirs("new-agent")

        memory_dir = patch_data_dir / "agents" / "new-agent" / "memory"
        long_term_dir = memory_dir / "long-term"

        assert memory_dir.exists()
        assert long_term_dir.exists()
