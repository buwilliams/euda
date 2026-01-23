"""
Progress Awareness - Detects when agents are stuck or not making progress.

Provides:
- Tool call pattern detection (same tool with same inputs)
- Iteration outcome tracking (jobs completed/created)
- Stuck condition detection with configurable thresholds
"""

from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ToolCall:
    """Record of a single tool call."""
    tool_name: str
    tool_input: dict
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IterationOutcome:
    """Record of what happened in an iteration."""
    iteration: int
    jobs_completed: int = 0
    jobs_created: int = 0
    tool_calls: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class ProgressTracker:
    """Tracks agent progress and detects stuck patterns.

    This is a more comprehensive progress tracker that can be used
    for detailed analysis. The basic stuck detection is in Metacognition.
    """

    def __init__(self, agent_id: str, config: dict = None):
        """Initialize progress tracker.

        Args:
            agent_id: The agent being tracked
            config: Progress configuration dict
        """
        self.agent_id = agent_id
        self.config = config or {}

        # Tracking state
        self.tool_history: List[ToolCall] = []
        self.iteration_outcomes: List[IterationOutcome] = []
        self.current_iteration: int = 0

    def record_tool_call(self, tool_name: str, tool_input: dict):
        """Record a tool call for pattern detection.

        Args:
            tool_name: Name of the tool called
            tool_input: Input parameters to the tool
        """
        self.tool_history.append(ToolCall(
            tool_name=tool_name,
            tool_input=tool_input
        ))

        # Keep history bounded
        max_history = self.config.get("max_history", 200)
        if len(self.tool_history) > max_history:
            self.tool_history = self.tool_history[-max_history // 2:]

    def record_iteration_end(self, jobs_completed: int = 0, jobs_created: int = 0, tool_calls: int = 0):
        """Record what changed during an iteration.

        Args:
            jobs_completed: Number of jobs marked complete
            jobs_created: Number of new jobs created
            tool_calls: Number of tool calls made
        """
        self.current_iteration += 1
        self.iteration_outcomes.append(IterationOutcome(
            iteration=self.current_iteration,
            jobs_completed=jobs_completed,
            jobs_created=jobs_created,
            tool_calls=tool_calls
        ))

        # Keep outcomes bounded
        max_outcomes = self.config.get("max_outcomes", 50)
        if len(self.iteration_outcomes) > max_outcomes:
            self.iteration_outcomes = self.iteration_outcomes[-max_outcomes // 2:]

    def check_repeated_tools(self, count: int = 3) -> Optional[str]:
        """Check if the same tool was called repeatedly with identical inputs.

        Args:
            count: Number of repeated calls to trigger

        Returns:
            Reason string if stuck, None if OK
        """
        if len(self.tool_history) < count:
            return None

        recent = self.tool_history[-count:]
        first = recent[0]

        if all(
            t.tool_name == first.tool_name and
            t.tool_input == first.tool_input
            for t in recent
        ):
            return f"Same tool '{first.tool_name}' called {count} times with identical inputs"

        return None

    def check_no_progress(self, iterations: int = 5) -> Optional[str]:
        """Check if no progress has been made over recent iterations.

        Args:
            iterations: Number of iterations to check

        Returns:
            Reason string if stuck, None if making progress
        """
        if len(self.iteration_outcomes) < iterations:
            return None

        recent = self.iteration_outcomes[-iterations:]

        # Check if any jobs were completed or created
        total_completed = sum(o.jobs_completed for o in recent)
        total_created = sum(o.jobs_created for o in recent)

        if total_completed == 0 and total_created == 0:
            return f"No jobs completed or created in last {iterations} iterations"

        return None

    def check_tool_sequence_loop(self, sequence_length: int = 3, repetitions: int = 2) -> Optional[str]:
        """Check if the same sequence of tools is repeating.

        Args:
            sequence_length: Length of sequence to look for
            repetitions: Number of times sequence must repeat

        Returns:
            Reason string if stuck, None if OK
        """
        required_history = sequence_length * repetitions
        if len(self.tool_history) < required_history:
            return None

        recent = self.tool_history[-required_history:]

        # Extract tool names only for sequence matching
        tool_names = [t.tool_name for t in recent]

        # Check if we have repeating sequences
        sequence = tool_names[:sequence_length]

        for i in range(1, repetitions):
            start = i * sequence_length
            end = start + sequence_length
            if tool_names[start:end] != sequence:
                return None

        sequence_str = " -> ".join(sequence)
        return f"Tool sequence '{sequence_str}' repeated {repetitions} times"

    def check_stuck(self) -> Optional[str]:
        """Check all stuck conditions.

        Returns:
            First reason found, or None if making progress
        """
        max_repeated = self.config.get("max_repeated_tool_calls", 3)
        max_no_progress = self.config.get("max_no_progress_iterations", 5)

        # Check repeated tools
        reason = self.check_repeated_tools(max_repeated)
        if reason:
            return reason

        # Check no progress
        reason = self.check_no_progress(max_no_progress)
        if reason:
            return reason

        # Check tool sequence loops
        reason = self.check_tool_sequence_loop()
        if reason:
            return reason

        return None

    def reset(self):
        """Reset tracking for new work cycle."""
        self.tool_history = []
        self.iteration_outcomes = []
        self.current_iteration = 0

    def get_summary(self) -> dict:
        """Get a summary of progress tracking state.

        Returns:
            Dict with tracking statistics
        """
        return {
            "agent_id": self.agent_id,
            "current_iteration": self.current_iteration,
            "tool_history_length": len(self.tool_history),
            "iteration_outcomes_length": len(self.iteration_outcomes),
            "is_stuck": self.check_stuck() is not None,
            "stuck_reason": self.check_stuck()
        }
