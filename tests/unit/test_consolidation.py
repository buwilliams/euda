"""
Unit tests for consolidation module.

Tests for src.tools.system.consolidation/consolidate.py
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestIdentitySectionParsing:
    """Test identity markdown parsing.

    Spec: specs/2_data.md - Identity Schema
    """

    def test_parse_identity_with_title_and_sections(self):
        """Parse structured identity with title and sections."""
        from src.tools.system.consolidation.consolidate import (
            _parse_identity_sections
        )

        content = """# User

## Purpose

To be productive and learn new things.

## Behavioral Rules

I must always be honest.
I must not procrastinate.

## Interests

- Python programming
- Machine learning
"""

        title, sections = _parse_identity_sections(content)

        assert title == "# User"
        assert "purpose" in sections
        assert "To be productive" in sections["purpose"]
        assert "behavioral_rules" in sections
        assert "I must always be honest" in sections["behavioral_rules"]
        assert "interests" in sections
        assert "Python programming" in sections["interests"]

    def test_parse_identity_without_title(self):
        """Parse identity without a title line."""
        from src.tools.system.consolidation.consolidate import (
            _parse_identity_sections
        )

        content = """## Purpose

To help users.

## Voice

Friendly and helpful.
"""

        title, sections = _parse_identity_sections(content)

        assert title == ""
        assert "purpose" in sections
        assert "voice" in sections

    def test_parse_identity_with_preamble(self):
        """Parse identity with unstructured content before sections."""
        from src.tools.system.consolidation.consolidate import (
            _parse_identity_sections
        )

        content = """# Agent

This is some introductory text that comes before any sections.
It should be preserved as preamble.

## Purpose

Main purpose here.
"""

        title, sections = _parse_identity_sections(content)

        assert title == "# Agent"
        assert "_preamble" in sections
        assert "introductory text" in sections["_preamble"]
        assert "purpose" in sections

    def test_parse_identity_with_unrecognized_sections(self):
        """Parse identity with custom sections not in standard schema."""
        from src.tools.system.consolidation.consolidate import (
            _parse_identity_sections
        )

        content = """# User

## Purpose

Main purpose.

## Core Promise

I will always help.

## Custom Section

Custom content.
"""

        title, sections = _parse_identity_sections(content)

        assert "purpose" in sections
        # Unrecognized sections stored with _other_ prefix
        assert "_other_Core Promise" in sections
        assert "_other_Custom Section" in sections

    def test_parse_identity_with_date_suffix_in_header(self):
        """Parse identity with date suffix in section header."""
        from src.tools.system.consolidation.consolidate import (
            _parse_identity_sections
        )

        content = """# User

## Purpose (2025-01-18)

Purpose with date suffix.
"""

        title, sections = _parse_identity_sections(content)

        # Date suffix should be stripped when matching section key
        assert "purpose" in sections
        assert "Purpose with date suffix" in sections["purpose"]


class TestIdentityBuilding:
    """Test building identity markdown from sections."""

    def test_build_identity_with_all_sections(self):
        """Build identity markdown from complete sections dict."""
        from src.tools.system.consolidation.consolidate import (
            _build_identity_markdown
        )

        sections = {
            "purpose": "To help users achieve their goals.",
            "behavioral_rules": "I must be honest.\nI must not deceive.",
            "voice": "Friendly and professional.",
        }

        result = _build_identity_markdown("# User", sections, "user")

        assert result.startswith("# User")
        assert "## Purpose" in result
        assert "To help users achieve their goals" in result
        assert "## Behavioral Rules" in result
        assert "## Voice" in result

    def test_build_identity_generates_title_if_missing(self):
        """Build identity generates title from agent_id if not provided."""
        from src.tools.system.consolidation.consolidate import (
            _build_identity_markdown
        )

        sections = {"purpose": "Testing."}

        result = _build_identity_markdown("", sections, "test-agent")

        assert result.startswith("# Test-Agent")

    def test_build_identity_includes_preamble(self):
        """Build identity includes preamble content."""
        from src.tools.system.consolidation.consolidate import (
            _build_identity_markdown
        )

        sections = {
            "_preamble": "Introductory text here.",
            "purpose": "Main purpose.",
        }

        result = _build_identity_markdown("# Agent", sections, "agent")

        # Preamble should appear before sections
        preamble_pos = result.find("Introductory text")
        purpose_pos = result.find("## Purpose")
        assert preamble_pos < purpose_pos

    def test_build_identity_preserves_other_sections(self):
        """Build identity preserves unrecognized sections."""
        from src.tools.system.consolidation.consolidate import (
            _build_identity_markdown
        )

        sections = {
            "purpose": "Main purpose.",
            "_other_Core Promise": "I will always help.",
        }

        result = _build_identity_markdown("# Agent", sections, "agent")

        assert "## Core Promise" in result
        assert "I will always help" in result


class TestSectionMerging:
    """Test merging content into identity sections."""

    def test_merge_into_empty_section(self):
        """Merge content into empty section."""
        from src.tools.system.consolidation.consolidate import (
            _merge_section_content
        )

        result = _merge_section_content("", "New content here.")

        assert result == "New content here."

    def test_merge_empty_into_existing(self):
        """Merge empty content preserves existing."""
        from src.tools.system.consolidation.consolidate import (
            _merge_section_content
        )

        result = _merge_section_content("Existing content.", "")

        assert result == "Existing content."

    def test_merge_prose_appends_with_paragraph_break(self):
        """Merge prose content appends with paragraph break."""
        from src.tools.system.consolidation.consolidate import (
            _merge_section_content
        )

        existing = "First paragraph of prose."
        new = "Second paragraph of prose."

        result = _merge_section_content(existing, new)

        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "\n\n" in result  # Paragraph break

    def test_merge_list_appends_without_duplicates(self):
        """Merge list content appends new items, avoiding duplicates."""
        from src.tools.system.consolidation.consolidate import (
            _merge_section_content
        )

        existing = "- Item one\n- Item two"
        new = "- Item two\n- Item three"

        result = _merge_section_content(existing, new)

        assert "Item one" in result
        assert result.count("Item two") == 1  # No duplicate
        assert "Item three" in result

    def test_merge_behavioral_rules_list(self):
        """Merge behavioral rules (I must/must not format)."""
        from src.tools.system.consolidation.consolidate import (
            _merge_section_content
        )

        existing = "I must be honest.\nI must not lie."
        new = "I must not lie.\nI must be helpful."

        result = _merge_section_content(existing, new)

        assert "I must be honest" in result
        assert result.lower().count("i must not lie") == 1  # No duplicate
        assert "I must be helpful" in result


class TestIdentityUpdate:
    """Test updating agent identity with new information."""

    def test_update_identity_structured_updates(self, tmp_path):
        """Update identity with structured section updates."""
        from src.tools.system.consolidation.consolidate import (
            _update_identity
        )

        # Create mock consolidation object
        consolidation = MagicMock()
        identity_path = tmp_path / "identity.md"
        identity_path.write_text("# User\n\n## Purpose\n\nOriginal purpose.\n")
        consolidation._get_identity_path.return_value = identity_path
        consolidation.agent.id = "user"

        updates = {
            "purpose": "Additional purpose info.",
            "interests": "- New interest",
        }

        _update_identity(consolidation, updates)

        result = identity_path.read_text()
        assert "Original purpose" in result
        assert "Additional purpose info" in result
        assert "## Interests" in result
        assert "New interest" in result

    def test_update_identity_legacy_string_format(self, tmp_path):
        """Update identity with legacy string format for backwards compatibility."""
        from src.tools.system.consolidation.consolidate import (
            _update_identity
        )

        consolidation = MagicMock()
        identity_path = tmp_path / "identity.md"
        identity_path.write_text("# User\n\nOriginal content.\n")
        consolidation._get_identity_path.return_value = identity_path
        consolidation.agent.id = "user"

        _update_identity(consolidation, "Legacy update text.")

        result = identity_path.read_text()
        assert "Original content" in result
        assert "Reflection Update" in result
        assert "Legacy update text" in result

    def test_update_identity_creates_file_if_missing(self, tmp_path):
        """Update identity creates file if it doesn't exist."""
        from src.tools.system.consolidation.consolidate import (
            _update_identity
        )

        consolidation = MagicMock()
        identity_path = tmp_path / "identity.md"
        consolidation._get_identity_path.return_value = identity_path
        consolidation.agent_id = "new-agent"

        updates = {"purpose": "New agent purpose."}

        _update_identity(consolidation, updates)

        assert identity_path.exists()
        result = identity_path.read_text()
        assert "# New-Agent" in result
        assert "New agent purpose" in result


class TestYearBoundarySnapshots:
    """Test historical identity snapshots at year boundaries.

    Spec: specs/2_data.md - Historical Identity Snapshots
    """

    def test_snapshot_created_in_first_week_of_year(self, tmp_path):
        """Snapshot created when in first week of new year."""
        from src.tools.system.consolidation.consolidate import (
            _maybe_snapshot_identity
        )

        consolidation = MagicMock()
        identity_path = tmp_path / "identity.md"
        identity_path.write_text("# User\n\nCurrent identity content.\n")
        consolidation._get_identity_path.return_value = identity_path

        # Historical path for previous year
        historical_path = tmp_path / "identity.2025.md"
        consolidation._get_historical_identity_path.return_value = historical_path
        consolidation.agent.id = "user"
        consolidation.logger = MagicMock()

        # Mock datetime to be in first week of January
        with patch('src.tools.system.consolidation.consolidate.datetime') as mock_dt:
            mock_dt.now.return_value.month = 1
            mock_dt.now.return_value.day = 3
            mock_dt.now.return_value.strftime.return_value = "2026"

            _maybe_snapshot_identity(consolidation)

        assert historical_path.exists()
        assert "Current identity content" in historical_path.read_text()

    def test_no_snapshot_after_first_week(self, tmp_path):
        """No snapshot created after first week of year."""
        from src.tools.system.consolidation.consolidate import (
            _maybe_snapshot_identity
        )

        consolidation = MagicMock()
        identity_path = tmp_path / "identity.md"
        identity_path.write_text("# User\n\nContent.\n")
        consolidation._get_identity_path.return_value = identity_path

        historical_path = tmp_path / "identity.2025.md"
        consolidation._get_historical_identity_path.return_value = historical_path
        consolidation.logger = MagicMock()

        # Mock datetime to be after first week
        with patch('src.tools.system.consolidation.consolidate.datetime') as mock_dt:
            mock_dt.now.return_value.month = 1
            mock_dt.now.return_value.day = 15  # After first week

            _maybe_snapshot_identity(consolidation)

        assert not historical_path.exists()

    def test_no_duplicate_snapshot(self, tmp_path):
        """No snapshot created if one already exists."""
        from src.tools.system.consolidation.consolidate import (
            _maybe_snapshot_identity
        )

        consolidation = MagicMock()
        identity_path = tmp_path / "identity.md"
        identity_path.write_text("# User\n\nCurrent content.\n")
        consolidation._get_identity_path.return_value = identity_path

        # Pre-existing historical snapshot
        historical_path = tmp_path / "identity.2025.md"
        historical_path.write_text("# User\n\nOld snapshot.\n")
        consolidation._get_historical_identity_path.return_value = historical_path
        consolidation.logger = MagicMock()

        with patch('src.tools.system.consolidation.consolidate.datetime') as mock_dt:
            mock_dt.now.return_value.month = 1
            mock_dt.now.return_value.day = 3

            _maybe_snapshot_identity(consolidation)

        # Should still contain old content, not overwritten
        assert "Old snapshot" in historical_path.read_text()
        assert "Current content" not in historical_path.read_text()
