"""
Unit tests for system tools module.

Tests for src/tools/system/system.py

Design: specs/1_agents.md - Work Cycle
- Agent calls done_working when work is complete
- Agent decides when any topic is complete
"""

import pytest
from unittest.mock import MagicMock, patch


class TestDoneWorking:
    """Test done_working tool.

    Design: specs/1_agents.md - "Agent works autonomously until calling done_working"
    """

    def test_done_working_sets_flag(self):
        """done_working sets agent._work_done = True.

        Design: This signals the work cycle loop to exit.
        """
        from src.core.system.system import done_working, set_agent_context, clear_agent_context

        # Mock agent
        mock_agent = MagicMock()
        mock_agent._work_done = False
        mock_agent._log = MagicMock()

        set_agent_context(mock_agent)
        try:
            result = done_working("Completed all tasks")

            assert mock_agent._work_done is True
            assert result["status"] == "acknowledged"
        finally:
            clear_agent_context()

    def test_done_working_logs_summary(self):
        """done_working logs the completion summary.

        Design: Logging provides visibility into what agents accomplished.
        """
        from src.core.system.system import done_working, set_agent_context, clear_agent_context

        mock_agent = MagicMock()
        mock_agent._log = MagicMock()

        set_agent_context(mock_agent)
        try:
            done_working("Processed 3 topics")

            mock_agent._log.assert_called_with("done_working", {"summary": "Processed 3 topics"})
        finally:
            clear_agent_context()

    def test_done_working_without_summary(self):
        """done_working works without a summary."""
        from src.core.system.system import done_working, set_agent_context, clear_agent_context

        mock_agent = MagicMock()
        mock_agent._log = MagicMock()

        set_agent_context(mock_agent)
        try:
            result = done_working()

            assert result["status"] == "acknowledged"
            mock_agent._log.assert_called_with("done_working", None)
        finally:
            clear_agent_context()

    def test_done_working_without_context(self):
        """done_working works even without agent context.

        This can happen in testing or standalone usage.
        """
        from src.core.system.system import done_working, clear_agent_context

        clear_agent_context()
        result = done_working("Test")

        # Should not raise, just return result
        assert result["status"] == "acknowledged"


class TestAgentContext:
    """Test agent context management."""

    def test_set_and_get_context(self):
        """Agent context can be set and retrieved."""
        from src.core.system.system import (
            set_agent_context, get_agent_context, clear_agent_context
        )

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"

        set_agent_context(mock_agent)
        try:
            context = get_agent_context()
            assert context is mock_agent
            assert context.id == "test-agent"
        finally:
            clear_agent_context()

    def test_clear_context(self):
        """Agent context can be cleared."""
        from src.core.system.system import (
            set_agent_context, get_agent_context, clear_agent_context
        )

        set_agent_context(MagicMock())
        clear_agent_context()

        assert get_agent_context() is None


class TestGetCurrentDate:
    """Test get_current_date tool."""

    def test_get_current_date_returns_date(self):
        """get_current_date returns current date info."""
        from src.core.system.dates import get_current_date

        result = get_current_date()

        assert "date" in result
        assert "weekday" in result

    def test_get_current_date_format(self):
        """get_current_date date format is ISO (YYYY-MM-DD)."""
        from src.core.system.dates import get_current_date

        result = get_current_date()

        # Should be YYYY-MM-DD format
        date = result["date"]
        assert len(date) == 10
        assert date[4] == "-"
        assert date[7] == "-"
