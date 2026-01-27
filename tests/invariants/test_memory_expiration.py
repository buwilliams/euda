"""
Memory Expiration Invariant Tests.

Spec: specs/2_data.md lines 45-49

These tests verify the memory expiration rules for short-term memory.

Invariants tested:
- Memory valid at exactly 90 days
- Memory expired at 91 days
- Expired entries filtered from list_memory
- Expired entries archived to long-term memory
"""

import json
import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time


@pytest.mark.invariant
class TestMemoryExpirationInvariants:
    """Test memory expiration invariants from spec."""

    def test_memory_valid_at_90_days(self, patch_data_dir):
        """Memory entry exactly 90 days old should still be valid.

        Spec: Entries expire after 90 days (3 months).

        Note: We use freezegun to set time to midnight to ensure consistent
        behavior, since _is_valid compares dates (at midnight) with the current
        datetime.
        """
        from src.core.data.memory import _is_valid, VALIDITY_DAYS

        # Verify constant
        assert VALIDITY_DAYS == 90

        # Use a fixed time to avoid edge cases with time of day
        with freeze_time("2024-06-15 00:00:00"):
            # Create entry from exactly 90 days ago
            date_90_days_ago = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            entry = {
                "id": "mem-test1",
                "date_mentioned": date_90_days_ago,
                "type": "idea",
                "short_description": "Test memory"
            }

            assert _is_valid(entry) is True, "Entry at exactly 90 days should be valid"

    def test_memory_expired_at_91_days(self, patch_data_dir):
        """Memory entry 91 days old should be expired.

        Spec: Entries older than 90 days are expired.
        """
        from src.core.data.memory import _is_valid

        # Create entry from 91 days ago
        date_91_days_ago = (datetime.now() - timedelta(days=91)).strftime('%Y-%m-%d')
        entry = {
            "id": "mem-test2",
            "date_mentioned": date_91_days_ago,
            "type": "idea",
            "short_description": "Test memory"
        }

        assert _is_valid(entry) is False, "Entry at 91 days should be expired"

    def test_expired_entries_filtered(self, patch_data_dir):
        """list_memory should exclude expired entries.

        Spec: Only valid (non-expired) entries returned.
        """
        from src.core.data.memory import add_memory, list_memory, _save_entries, _load_entries

        agent_id = "test-agent"

        # Ensure memory directory exists
        memory_dir = patch_data_dir / "agents" / agent_id / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Create entries with different ages
        today = datetime.now().strftime('%Y-%m-%d')
        old_date = (datetime.now() - timedelta(days=91)).strftime('%Y-%m-%d')

        entries = [
            {
                "id": "mem-valid",
                "date_mentioned": today,
                "type": "idea",
                "short_description": "Valid memory"
            },
            {
                "id": "mem-expired",
                "date_mentioned": old_date,
                "type": "idea",
                "short_description": "Expired memory"
            }
        ]
        _save_entries(entries, agent_id)

        # Patch write_long_term_memory to avoid side effects
        from unittest.mock import patch
        with patch('src.core.data.memory.write_long_term_memory'):
            result = list_memory(agent_id)

        # Only valid entry should be returned
        assert len(result) == 1
        assert result[0]["id"] == "mem-valid"

    def test_expired_entries_archived(self, patch_data_dir):
        """Expired entries should be archived to long-term memory.

        Spec: Expired memories are preserved in long-term memory.
        """
        from src.core.data.memory import list_memory, _save_entries
        from unittest.mock import patch, MagicMock

        agent_id = "test-agent"

        # Ensure memory directory exists
        memory_dir = patch_data_dir / "agents" / agent_id / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Create expired entry
        old_date = (datetime.now() - timedelta(days=91)).strftime('%Y-%m-%d')
        entries = [
            {
                "id": "mem-expired",
                "date_mentioned": old_date,
                "type": "learning",
                "short_description": "Expired learning"
            }
        ]
        _save_entries(entries, agent_id)

        # Mock write_long_term_memory to verify it's called
        with patch('src.core.data.memory.write_long_term_memory') as mock_write:
            list_memory(agent_id)

            # Verify archive was called
            mock_write.assert_called_once()
            call_args = mock_write.call_args
            assert "Expired learning" in call_args.kwargs.get("content", "")
            assert call_args.kwargs.get("agent_id") == agent_id


@pytest.mark.invariant
class TestMemoryTypes:
    """Test valid memory types."""

    def test_valid_memory_types(self):
        """Only specified types should be valid.

        Spec: person, place, thing, goal, concern, idea, learning, behavior
        """
        from src.core.data.memory import VALID_TYPES

        expected = {"person", "place", "thing", "goal", "concern", "idea", "learning", "behavior"}
        assert VALID_TYPES == expected

    def test_add_memory_rejects_invalid_type(self, patch_data_dir):
        """add_memory should reject invalid types.

        Spec: Type must be one of the valid types.
        """
        from src.core.data.memory import add_memory

        result = add_memory(
            short_description="Test",
            type="invalid_type",
            agent_id="test-agent"
        )

        assert "error" in result

    def test_add_memory_accepts_valid_types(self, patch_data_dir):
        """add_memory should accept all valid types.

        Spec: All specified types should work.
        """
        from src.core.data.memory import add_memory, VALID_TYPES

        agent_id = "test-agent"

        # Ensure memory directory exists
        memory_dir = patch_data_dir / "agents" / agent_id / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        for memory_type in VALID_TYPES:
            result = add_memory(
                short_description=f"Test {memory_type}",
                type=memory_type,
                agent_id=agent_id
            )
            assert "error" not in result, f"Type '{memory_type}' should be accepted"
            assert result["type"] == memory_type


@pytest.mark.invariant
class TestMemoryDateValidation:
    """Test memory date handling edge cases."""

    def test_missing_date_is_invalid(self):
        """Entry without date_mentioned should be invalid."""
        from src.core.data.memory import _is_valid

        entry = {
            "id": "mem-nodate",
            "type": "idea",
            "short_description": "No date"
        }

        assert _is_valid(entry) is False

    def test_malformed_date_is_invalid(self):
        """Entry with malformed date should be invalid."""
        from src.core.data.memory import _is_valid

        entry = {
            "id": "mem-baddate",
            "date_mentioned": "not-a-date",
            "type": "idea",
            "short_description": "Bad date"
        }

        assert _is_valid(entry) is False

    def test_future_date_is_valid(self):
        """Entry with future date should be valid (just mentioned early)."""
        from src.core.data.memory import _is_valid

        future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        entry = {
            "id": "mem-future",
            "date_mentioned": future_date,
            "type": "idea",
            "short_description": "Future memory"
        }

        assert _is_valid(entry) is True
