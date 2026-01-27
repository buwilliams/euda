"""
Integration tests for consolidation with LLM mocks.

Tests the consolidation append and consolidate phases using MockLLMClient
to verify:
- Memory extraction from conversations
- Identity updates based on patterns
- Proper JSON parsing of LLM responses

Spec: docs/3_system.md - Consolidation section
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from tests.fixtures.llm import MockLLMClient
from tests.fixtures.llm.mock_client import MockResponse


class TestAppendPhaseWithMockLLM:
    """Test consolidation append phase with mocked LLM."""

    def _create_consolidation(self, tmp_path):
        """Create a Consolidation instance with mock agent."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.identity = "A helpful test assistant."

        consolidation = Consolidation(mock_agent)

        # Create required directories
        memory_dir = tmp_path / "agents" / "test-agent" / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "long-term").mkdir(exist_ok=True)

        return consolidation

    def test_parse_items_extracts_valid_json(self):
        """_parse_items correctly extracts items from JSON response."""
        from plugins.core.system.consolidation.append import _parse_items

        response = '''[
          {"type": "person", "short_description": "John Doe - colleague"},
          {"type": "goal", "short_description": "Complete project by Friday"}
        ]'''

        items = _parse_items(response)

        assert len(items) == 2
        assert items[0]["type"] == "person"
        assert "John Doe" in items[0]["short_description"]
        assert items[1]["type"] == "goal"

    def test_parse_items_handles_markdown_code_block(self):
        """_parse_items handles JSON wrapped in markdown code blocks."""
        from plugins.core.system.consolidation.append import _parse_items

        response = '''```json
[
  {"type": "idea", "short_description": "New feature concept"}
]
```'''

        items = _parse_items(response)

        assert len(items) == 1
        assert items[0]["type"] == "idea"

    def test_parse_items_validates_types(self):
        """_parse_items filters out invalid memory types."""
        from plugins.core.system.consolidation.append import _parse_items

        response = '''[
          {"type": "person", "short_description": "Valid person"},
          {"type": "invalid_type", "short_description": "Should be filtered"},
          {"type": "goal", "short_description": "Valid goal"}
        ]'''

        items = _parse_items(response)

        assert len(items) == 2
        types = [i["type"] for i in items]
        assert "invalid_type" not in types

    def test_parse_items_validates_date_format(self):
        """_parse_items validates date_expected format."""
        from plugins.core.system.consolidation.append import _parse_items

        response = '''[
          {"type": "goal", "short_description": "Valid date", "date_expected": "2025-01-31"},
          {"type": "goal", "short_description": "Invalid date", "date_expected": "not-a-date"}
        ]'''

        items = _parse_items(response)

        assert items[0]["date_expected"] == "2025-01-31"
        assert items[1]["date_expected"] is None

    def test_parse_items_handles_empty_response(self):
        """_parse_items returns empty list for empty array."""
        from plugins.core.system.consolidation.append import _parse_items

        items = _parse_items("[]")
        assert items == []

    def test_parse_items_handles_malformed_json(self):
        """_parse_items returns empty list for invalid JSON."""
        from plugins.core.system.consolidation.append import _parse_items

        items = _parse_items("This is not JSON")
        assert items == []

    def test_parse_items_truncates_long_descriptions(self):
        """_parse_items truncates descriptions over 500 chars."""
        from plugins.core.system.consolidation.append import _parse_items

        long_desc = "x" * 600
        response = f'[{{"type": "idea", "short_description": "{long_desc}"}}]'

        items = _parse_items(response)

        assert len(items[0]["short_description"]) == 500


class TestAppendPhaseWithFixtures:
    """Test append phase using pre-recorded fixtures."""

    def test_append_fixture_returns_memory_items(self, tmp_path):
        """Append fixture returns properly formatted memory items."""
        from plugins.core.system.consolidation.append import _parse_items

        mock = MockLLMClient.from_fixture("append")

        # Get a response that should return items
        response = mock.responses[0].to_response()
        text = response.content[0].text

        items = _parse_items(text)

        # Should have extracted some items
        assert len(items) >= 1
        # Items should have required fields
        for item in items:
            assert "type" in item
            assert "short_description" in item

    def test_append_fixture_empty_scenario(self):
        """Append fixture returns empty list for trivial conversations."""
        from plugins.core.system.consolidation.append import _parse_items

        mock = MockLLMClient.from_fixture("append")

        # Find the empty scenario
        empty_response = None
        for resp in mock.responses:
            if resp.scenario == "append_empty":
                empty_response = resp
                break

        if empty_response:
            items = _parse_items(empty_response.text)
            assert items == []


class TestAddItemsToMemory:
    """Test memory deduplication and cross-pollination."""

    def _patch_memory_dirs(self, tmp_path):
        """Create patches for memory module directories."""
        return [
            patch("plugins.core.data.memory.DATA_DIR", tmp_path),
            patch("plugins.core.data.memory.AGENTS_DIR", tmp_path / "agents")
        ]

    def test_add_items_avoids_duplicates(self, tmp_path):
        """_add_items_to_memory avoids adding duplicate descriptions."""
        from plugins.core.system.consolidation.append import _add_items_to_memory

        patches = self._patch_memory_dirs(tmp_path)
        for p in patches:
            p.start()
        try:
            # Create agent directory
            agent_dir = tmp_path / "agents" / "test-agent" / "memory"
            agent_dir.mkdir(parents=True, exist_ok=True)

            existing_memory = [
                {"id": "mem-1", "short_description": "Existing item", "type": "idea"}
            ]

            new_items = [
                {"type": "idea", "short_description": "Existing item"},  # Duplicate
                {"type": "goal", "short_description": "New item"}  # New
            ]

            count = _add_items_to_memory(new_items, existing_memory, "test-agent")

            assert count == 1  # Only the new item
            assert len(existing_memory) == 2
        finally:
            for p in patches:
                p.stop()

    def test_add_items_generates_ids(self, tmp_path):
        """_add_items_to_memory generates unique IDs for new items."""
        from plugins.core.system.consolidation.append import _add_items_to_memory

        patches = self._patch_memory_dirs(tmp_path)
        for p in patches:
            p.start()
        try:
            agent_dir = tmp_path / "agents" / "test-agent" / "memory"
            agent_dir.mkdir(parents=True, exist_ok=True)

            existing_memory = []
            new_items = [
                {"type": "idea", "short_description": "First idea"},
                {"type": "idea", "short_description": "Second idea"}
            ]

            _add_items_to_memory(new_items, existing_memory, "test-agent")

            ids = [item["id"] for item in existing_memory]
            assert all(id.startswith("mem-") for id in ids)
            assert len(set(ids)) == 2  # Unique IDs
        finally:
            for p in patches:
                p.stop()


