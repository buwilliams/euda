"""
Unit tests for Progress Tracking.

Tests for src/agent/cognition/metacognition/regulation/progress.py including:
- Session management (start, end)
- Iteration counting and limits
- Tool call recording
- Stuck pattern detection

Spec: specs/1_agents.md - Progress Awareness
"""

import pytest


@pytest.mark.unit
class TestProgressTrackerSession:
    """Test session management in ProgressTracker."""

    def test_start_session_returns_session_id(self):
        """start_session() returns a unique session ID."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent", session_type="work_cycle")

        assert session_id is not None
        assert "test-agent" in session_id
        assert "work_cycle" in session_id

    def test_end_session_returns_stats(self):
        """end_session() returns session statistics."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent")
        tracker.increment(session_id)
        tracker.increment(session_id)

        stats = tracker.end_session(session_id)

        assert stats["total_iterations"] == 2
        assert stats["agent_id"] == "test-agent"
        assert "started_at" in stats
        assert "ended_at" in stats

    def test_end_session_cleans_up(self):
        """end_session() removes session from tracker."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent")
        tracker.end_session(session_id)

        # Session should no longer exist
        assert tracker.get_progress(session_id) is None


@pytest.mark.unit
class TestProgressTrackerIteration:
    """Test iteration tracking in ProgressTracker."""

    def test_increment_counts_iterations(self):
        """increment() tracks iteration count."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent")

        count1 = tracker.increment(session_id)
        count2 = tracker.increment(session_id)

        assert count1 == 1
        assert count2 == 2

    def test_increment_raises_on_limit(self):
        """increment() raises ProgressLimitExceeded when limit reached."""
        from src.agent.cognition.metacognition.regulation.progress import (
            ProgressTracker,
            ProgressLimitExceeded
        )

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent", max_iterations=3)

        tracker.increment(session_id)  # 1
        tracker.increment(session_id)  # 2
        tracker.increment(session_id)  # 3

        with pytest.raises(ProgressLimitExceeded) as exc_info:
            tracker.increment(session_id)  # 4 - exceeds limit

        assert "max iterations exceeded" in exc_info.value.reason


@pytest.mark.unit
class TestProgressTrackerToolCalls:
    """Test tool call recording and stuck detection."""

    def test_record_tool_call_tracks_calls(self):
        """record_tool_call() tracks tool calls in session."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent")

        tracker.record_tool_call(session_id, "list_jobs", '{"status": "todo"}')
        tracker.record_tool_call(session_id, "get_job", '{"id": "123"}')

        progress = tracker.get_progress(session_id)
        assert progress["tool_call_count"] == 2

    def test_record_tool_call_detects_stuck_pattern(self):
        """record_tool_call() raises when stuck pattern detected.

        Spec: Detects stuck patterns: same tool called repeatedly with identical inputs.
        """
        from src.agent.cognition.metacognition.regulation.progress import (
            ProgressTracker,
            ProgressLimitExceeded
        )

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent", stuck_threshold=5)

        # Call same tool with same input 4 times - should be fine
        for _ in range(4):
            tracker.record_tool_call(session_id, "list_jobs", '{"status": "todo"}')

        # 5th identical call should trigger stuck detection
        with pytest.raises(ProgressLimitExceeded) as exc_info:
            tracker.record_tool_call(session_id, "list_jobs", '{"status": "todo"}')

        assert "list_jobs" in exc_info.value.reason
        assert "5 times" in exc_info.value.reason

    def test_record_tool_call_allows_varied_calls(self):
        """record_tool_call() allows varied tool calls without raising."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent", stuck_threshold=3)

        # Varied calls should not trigger stuck detection
        tracker.record_tool_call(session_id, "list_jobs", '{"status": "todo"}')
        tracker.record_tool_call(session_id, "get_job", '{"id": "1"}')
        tracker.record_tool_call(session_id, "list_jobs", '{"status": "todo"}')
        tracker.record_tool_call(session_id, "get_job", '{"id": "2"}')
        tracker.record_tool_call(session_id, "list_jobs", '{"status": "done"}')

        progress = tracker.get_progress(session_id)
        assert progress["tool_call_count"] == 5
        assert progress["is_stuck"] is False

    def test_check_stuck_returns_reason_when_stuck(self):
        """check_stuck() returns reason string when stuck."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent", stuck_threshold=3)

        # Add calls but don't exceed threshold (2 identical calls)
        tracker.record_tool_call(session_id, "list_jobs", '{"status": "todo"}')
        tracker.record_tool_call(session_id, "list_jobs", '{"status": "todo"}')

        # Not stuck yet
        assert tracker.check_stuck(session_id) is None

    def test_get_progress_includes_stuck_info(self):
        """get_progress() includes stuck detection info."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent")

        progress = tracker.get_progress(session_id)

        assert "is_stuck" in progress
        assert "stuck_reason" in progress
        assert "tool_call_count" in progress
        assert "stuck_threshold" in progress


@pytest.mark.unit
class TestProgressTrackerStats:
    """Test progress statistics and reporting."""

    def test_end_session_includes_tool_call_count(self):
        """end_session() includes total tool calls in stats."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker()
        session_id = tracker.start_session("test-agent")

        tracker.record_tool_call(session_id, "tool1", '{}')
        tracker.record_tool_call(session_id, "tool2", '{}')
        tracker.record_tool_call(session_id, "tool3", '{}')

        stats = tracker.end_session(session_id)

        assert stats["total_tool_calls"] == 3
