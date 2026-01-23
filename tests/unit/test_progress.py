"""
Unit tests for progress awareness module.

Tests for src/agent/cognition/metacognition/regulation/progress.py

Design: specs/1_agents.md - Progress Awareness
- Counts tool calls per iteration
- Detects stuck patterns (same tool with identical inputs)
- Breaks work cycle when stuck detected
"""

import pytest
from datetime import datetime


class TestProgressTracker:
    """Test ProgressTracker class."""

    def test_record_tool_call(self):
        """Tool calls are recorded in history."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")
        tracker.record_tool_call("list_jobs", {"status": "todo"})

        assert len(tracker.tool_history) == 1
        assert tracker.tool_history[0].tool_name == "list_jobs"
        assert tracker.tool_history[0].tool_input == {"status": "todo"}

    def test_history_bounded(self):
        """Tool history is bounded to prevent memory growth."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent", config={"max_history": 10})

        # Add more than max
        for i in range(20):
            tracker.record_tool_call("tool", {"i": i})

        # Should be trimmed
        assert len(tracker.tool_history) <= 10

    def test_record_iteration_end(self):
        """Iteration outcomes are recorded."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")
        tracker.record_iteration_end(jobs_completed=1, jobs_created=2, tool_calls=5)

        assert len(tracker.iteration_outcomes) == 1
        assert tracker.iteration_outcomes[0].jobs_completed == 1
        assert tracker.iteration_outcomes[0].jobs_created == 2
        assert tracker.iteration_outcomes[0].tool_calls == 5
        assert tracker.current_iteration == 1


class TestStuckDetection:
    """Test stuck pattern detection.

    Design: specs/1_agents.md - "Detects stuck patterns: same tool called
    repeatedly with identical inputs"
    """

    def test_repeated_tools_detected(self):
        """Same tool with identical inputs N times triggers stuck.

        Design: Repeated identical tool calls indicate no progress.
        """
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")

        # Call same tool 3 times with identical inputs
        for _ in range(3):
            tracker.record_tool_call("list_jobs", {"status": "todo"})

        reason = tracker.check_repeated_tools(count=3)

        assert reason is not None
        assert "list_jobs" in reason
        assert "3 times" in reason

    def test_different_inputs_not_stuck(self):
        """Same tool with different inputs is not stuck."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")

        tracker.record_tool_call("list_jobs", {"status": "todo"})
        tracker.record_tool_call("list_jobs", {"status": "completed"})
        tracker.record_tool_call("list_jobs", {"status": "archived"})

        reason = tracker.check_repeated_tools(count=3)
        assert reason is None

    def test_different_tools_not_stuck(self):
        """Different tools with same inputs is not stuck."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")

        tracker.record_tool_call("list_jobs", {"status": "todo"})
        tracker.record_tool_call("get_job", {"status": "todo"})
        tracker.record_tool_call("create_job", {"status": "todo"})

        reason = tracker.check_repeated_tools(count=3)
        assert reason is None

    def test_no_progress_detected(self):
        """No jobs completed/created over N iterations triggers stuck.

        Design: If agent isn't making progress (completing/creating jobs),
        it may be stuck in a loop.
        """
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")

        # 5 iterations with no progress
        for _ in range(5):
            tracker.record_iteration_end(jobs_completed=0, jobs_created=0, tool_calls=10)

        reason = tracker.check_no_progress(iterations=5)

        assert reason is not None
        assert "No jobs" in reason
        assert "5 iterations" in reason

    def test_progress_resets_stuck(self):
        """Completing a job resets the no-progress stuck condition."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")

        # 4 iterations with no progress
        for _ in range(4):
            tracker.record_iteration_end(jobs_completed=0, jobs_created=0, tool_calls=10)

        # 1 iteration with progress
        tracker.record_iteration_end(jobs_completed=1, jobs_created=0, tool_calls=5)

        reason = tracker.check_no_progress(iterations=5)
        assert reason is None

    def test_tool_sequence_loop_detected(self):
        """Repeating sequence of tools indicates loop.

        Design: A→B→C→A→B→C pattern suggests agent is in a loop.
        """
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")

        # Repeat sequence twice: A->B->C->A->B->C
        for _ in range(2):
            tracker.record_tool_call("tool_a", {})
            tracker.record_tool_call("tool_b", {})
            tracker.record_tool_call("tool_c", {})

        reason = tracker.check_tool_sequence_loop(sequence_length=3, repetitions=2)

        assert reason is not None
        assert "repeated" in reason

    def test_check_stuck_aggregates_all_checks(self):
        """check_stuck() runs all stuck checks."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent", config={
            "max_repeated_tool_calls": 3,
            "max_no_progress_iterations": 5
        })

        # No stuck initially
        assert tracker.check_stuck() is None

        # Trigger repeated tools stuck
        for _ in range(3):
            tracker.record_tool_call("list_jobs", {"x": 1})

        assert tracker.check_stuck() is not None


class TestProgressTrackerReset:
    """Test reset functionality."""

    def test_reset_clears_state(self):
        """reset() clears all tracking state for new work cycle.

        Design: Each work cycle starts fresh.
        """
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")

        # Add some state
        tracker.record_tool_call("tool", {})
        tracker.record_iteration_end(jobs_completed=1)

        assert len(tracker.tool_history) > 0
        assert len(tracker.iteration_outcomes) > 0

        # Reset
        tracker.reset()

        assert len(tracker.tool_history) == 0
        assert len(tracker.iteration_outcomes) == 0
        assert tracker.current_iteration == 0


class TestProgressTrackerSummary:
    """Test summary functionality."""

    def test_get_summary(self):
        """get_summary() returns tracking statistics."""
        from src.agent.cognition.metacognition.regulation.progress import ProgressTracker

        tracker = ProgressTracker("test-agent")
        tracker.record_tool_call("tool", {})
        tracker.record_iteration_end()

        summary = tracker.get_summary()

        assert summary["agent_id"] == "test-agent"
        assert summary["current_iteration"] == 1
        assert summary["tool_history_length"] == 1
        assert summary["iteration_outcomes_length"] == 1
        assert "is_stuck" in summary
        assert "stuck_reason" in summary
