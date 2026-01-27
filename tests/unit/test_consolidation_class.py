"""
Unit tests for Consolidation class.

Tests for src.tools.system.consolidation/consolidation.py including:
- Initialization
- Append phase delegation
- Consolidate phase delegation
- Batch append
- Error handling

Spec: docs/3_system.md - Metacognition/Consolidation section
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

from tests.fixtures.llm import MockLLMClient, MockResponse


class TestConsolidationInitialization:
    """Test Consolidation class initialization."""

    def test_consolidation_initializes_with_agent(self):
        """Consolidation initializes with agent reference."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.config = {"consolidation": {"enabled": True}}

        consolidation = Consolidation(mock_agent)

        assert consolidation.agent == mock_agent

    def test_consolidation_creates_logger(self):
        """Consolidation creates a logger for consolidation events."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.config = {}

        consolidation = Consolidation(mock_agent)

        assert consolidation.logger is not None

    def test_consolidation_inherits_event_sink(self):
        """Consolidation inherits event sink from agent."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.config = {}
        mock_sink = MagicMock()
        mock_agent._event_sink = mock_sink

        consolidation = Consolidation(mock_agent)

        assert consolidation._event_sink == mock_sink


class TestConsolidationPaths:
    """Test path helper methods."""

    def _create_consolidation(self):
        """Create a Consolidation instance for testing."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.config = {}

        return Consolidation(mock_agent)

    def test_get_short_term_path(self):
        """_get_short_term_path returns correct path."""
        consolidation = self._create_consolidation()

        path = consolidation._get_short_term_path()

        assert "test-agent" in str(path)
        assert "memory" in str(path)
        assert "short-term.jsonl" in str(path)

    def test_get_long_term_dir_default_year(self):
        """_get_long_term_dir uses current year by default."""
        from datetime import datetime
        consolidation = self._create_consolidation()

        path = consolidation._get_long_term_dir()

        current_year = datetime.now().strftime("%Y")
        assert current_year in str(path)
        assert "long-term" in str(path)

    def test_get_long_term_dir_specific_year(self):
        """_get_long_term_dir uses provided year."""
        consolidation = self._create_consolidation()

        path = consolidation._get_long_term_dir(year="2023")

        assert "2023" in str(path)

    def test_get_identity_path(self):
        """_get_identity_path returns identity.md path."""
        consolidation = self._create_consolidation()

        path = consolidation._get_identity_path()

        assert "test-agent" in str(path)
        assert "identity.md" in str(path)

    def test_get_historical_identity_path(self):
        """_get_historical_identity_path returns year-specific path."""
        consolidation = self._create_consolidation()

        path = consolidation._get_historical_identity_path("2024")

        assert "test-agent" in str(path)
        assert "identity.2024.md" in str(path)


class TestConsolidationAppend:
    """Test Consolidation.append() method."""

    def _create_consolidation(self, tmp_path):
        """Create a Consolidation with mocked paths."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.identity = "A test agent."
        mock_agent.config = {}

        consolidation = Consolidation(mock_agent)
        return consolidation

    def test_append_delegates_to_append_phase(self, tmp_path):
        """append() calls append_phase function."""
        consolidation = self._create_consolidation(tmp_path)

        with patch("plugins.core.system.consolidation.append.append_phase") as mock_phase:
            mock_phase.return_value = 2

            consolidation.append("Hello", "Hi there!")

        mock_phase.assert_called_once()
        args = mock_phase.call_args[0]
        assert args[0] == consolidation
        assert args[1] == "Hello"
        assert args[2] == "Hi there!"

    def test_append_emits_events(self, tmp_path):
        """append() emits start and complete events."""
        consolidation = self._create_consolidation(tmp_path)
        events = []

        def capture_event(event, details):
            events.append(event)

        consolidation._event_sink = capture_event

        with patch("plugins.core.system.consolidation.append.append_phase", return_value=1):
            consolidation.append("Test", "Response")

        assert "append_start" in events
        assert "append_complete" in events

    def test_append_handles_errors_gracefully(self, tmp_path):
        """append() logs errors but doesn't raise."""
        consolidation = self._create_consolidation(tmp_path)

        with patch("plugins.core.system.consolidation.append.append_phase",
                   side_effect=Exception("LLM failed")):
            # Should not raise
            consolidation.append("Test", "Response")

    def test_append_logs_errors(self, tmp_path):
        """append() logs errors to consolidation logger."""
        consolidation = self._create_consolidation(tmp_path)
        consolidation.logger = MagicMock()

        with patch("plugins.core.system.consolidation.append.append_phase",
                   side_effect=Exception("Test error")):
            consolidation.append("Test", "Response")

        consolidation.logger.error.assert_called_once()


class TestConsolidationConsolidate:
    """Test Consolidation.consolidate() method."""

    def _create_consolidation(self):
        """Create a Consolidation for testing."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.identity = "A test agent."
        mock_agent.config = {}

        return Consolidation(mock_agent)

    def test_consolidate_delegates_to_consolidate_phase(self):
        """consolidate() calls consolidate_phase function."""
        consolidation = self._create_consolidation()

        with patch("plugins.core.system.consolidation.consolidate.consolidate_phase") as mock_phase:
            mock_phase.return_value = {"identity_updated": True}

            consolidation.consolidate()

        mock_phase.assert_called_once()

    def test_consolidate_emits_events(self):
        """consolidate() emits start and complete events."""
        consolidation = self._create_consolidation()
        events = []

        def capture_event(event, details):
            events.append(event)

        consolidation._event_sink = capture_event

        with patch("plugins.core.system.consolidation.consolidate.consolidate_phase",
                   return_value={"identity_updated": False}):
            consolidation.consolidate()

        assert "consolidate_start" in events
        assert "consolidate_complete" in events

    def test_consolidate_reraises_errors(self):
        """consolidate() re-raises errors for manager to handle."""
        consolidation = self._create_consolidation()

        with patch("plugins.core.system.consolidation.consolidate.consolidate_phase",
                   side_effect=Exception("Critical error")):
            with pytest.raises(Exception) as exc_info:
                consolidation.consolidate()

        assert "Critical error" in str(exc_info.value)

    def test_consolidate_logs_errors(self):
        """consolidate() logs errors before re-raising."""
        consolidation = self._create_consolidation()
        consolidation.logger = MagicMock()

        with patch("plugins.core.system.consolidation.consolidate.consolidate_phase",
                   side_effect=Exception("Test error")):
            try:
                consolidation.consolidate()
            except Exception:
                pass

        consolidation.logger.error.assert_called_once()


class TestConsolidationBatchAppend:
    """Test Consolidation.append_batch() method."""

    def _create_consolidation(self):
        """Create a Consolidation for testing."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.identity = "A test agent."
        mock_agent.config = {}

        return Consolidation(mock_agent)

    def test_append_batch_with_empty_list_returns_zero(self):
        """append_batch() returns 0 for empty exchanges."""
        consolidation = self._create_consolidation()

        result = consolidation.append_batch([])

        assert result == 0

    def test_append_batch_delegates_to_batch_phase(self):
        """append_batch() calls append_batch_phase function."""
        consolidation = self._create_consolidation()

        with patch("plugins.core.system.consolidation.append.append_batch_phase") as mock_phase:
            mock_phase.return_value = 3

            exchanges = [
                ("Message 1", "Response 1"),
                ("Message 2", "Response 2")
            ]
            result = consolidation.append_batch(exchanges)

        mock_phase.assert_called_once()
        assert result == 3

    def test_append_batch_emits_events(self):
        """append_batch() emits start and complete events."""
        consolidation = self._create_consolidation()
        events = []

        def capture_event(event, details):
            events.append((event, details))

        consolidation._event_sink = capture_event

        with patch("plugins.core.system.consolidation.append.append_batch_phase", return_value=1):
            consolidation.append_batch([("Test", "Response")])

        event_names = [e[0] for e in events]
        assert "append_batch_start" in event_names
        assert "append_batch_complete" in event_names

    def test_append_batch_includes_exchange_count_in_events(self):
        """append_batch() includes exchange_count in events."""
        consolidation = self._create_consolidation()
        events = []

        def capture_event(event, details):
            events.append((event, details))

        consolidation._event_sink = capture_event

        exchanges = [("M1", "R1"), ("M2", "R2"), ("M3", "R3")]
        with patch("plugins.core.system.consolidation.append.append_batch_phase", return_value=2):
            consolidation.append_batch(exchanges)

        start_event = next(e for e in events if e[0] == "append_batch_start")
        assert start_event[1]["exchange_count"] == 3

    def test_append_batch_handles_errors(self):
        """append_batch() handles errors gracefully and returns 0."""
        consolidation = self._create_consolidation()

        with patch("plugins.core.system.consolidation.append.append_batch_phase",
                   side_effect=Exception("Batch failed")):
            result = consolidation.append_batch([("Test", "Response")])

        assert result == 0

    def test_append_batch_logs_errors(self):
        """append_batch() logs errors to consolidation logger."""
        consolidation = self._create_consolidation()
        consolidation.logger = MagicMock()

        with patch("plugins.core.system.consolidation.append.append_batch_phase",
                   side_effect=Exception("Test error")):
            consolidation.append_batch([("Test", "Response")])

        consolidation.logger.error.assert_called_once()


class TestConsolidationConfig:
    """Test Consolidation configuration access."""

    def test_get_config_from_agent(self):
        """_get_config returns consolidation section from agent config."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.config = {
            "consolidation": {
                "enabled": True,
                "trigger": "time:evening"
            }
        }

        consolidation = Consolidation(mock_agent)
        config = consolidation._get_config()

        assert config["enabled"] is True
        assert config["trigger"] == "time:evening"

    def test_get_config_returns_empty_if_missing(self):
        """_get_config returns empty dict if consolidation not in config."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.config = {}

        consolidation = Consolidation(mock_agent)
        config = consolidation._get_config()

        assert config == {}


class TestEventSinkEmission:
    """Test event emission to sink."""

    def test_emit_to_sink_when_configured(self):
        """_emit_to_sink calls sink with agent_id."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.config = {}
        mock_sink = MagicMock()
        mock_agent._event_sink = mock_sink

        consolidation = Consolidation(mock_agent)
        consolidation._emit_to_sink("test_event", {"key": "value"})

        mock_sink.assert_called_once()
        args = mock_sink.call_args[0]
        assert args[0] == "test_event"
        assert args[1]["agent_id"] == "test-agent"
        assert args[1]["key"] == "value"

    def test_emit_to_sink_does_nothing_without_sink(self):
        """_emit_to_sink is no-op when sink not configured."""
        from plugins.core.system.consolidation import Consolidation

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent.config = {}
        # No _event_sink attribute

        consolidation = Consolidation(mock_agent)
        consolidation._event_sink = None

        # Should not raise
        consolidation._emit_to_sink("test_event", {"key": "value"})
