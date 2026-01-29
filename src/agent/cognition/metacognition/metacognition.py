"""
Metacognition - The agent's self-regulation system.

Metacognition is inherent to all agents and provides:
- Token awareness (budget tracking via llm.json)
- Action tracking (tool call telemetry)
- Progress awareness (stuck detection via ProgressTracker)
- Strategic planning (always enabled)

This is the Cognition subsystem of the agent ontology:
Agent = Identity + Cognition + Memory + Behavior

Where Cognition = Reasoning (prompts) + Metacognition (self-regulation)
"""

import json
from typing import Optional, TYPE_CHECKING

from .regulation.config import MetacognitionConfig
from .regulation.tokens import get_token_awareness, TokenAwareness, AgentState
from .regulation.progress import get_progress_tracker, ProgressTracker
from ..reasoning.planning import Planner
from src.logger import get_logger

if TYPE_CHECKING:
    from ...agent import Agent


class Metacognition:
    """The agent's self-awareness and self-regulation system.

    Every agent has metacognition - it's inherent, not optional.
    Just like every agent has an identity and memory.

    Metacognition provides:
    - Token awareness: Track tokens, enforce budgets (via llm.json)
    - Action tracking: Monitor tool calls for telemetry
    - Progress awareness: Detect stuck patterns (via ProgressTracker)
    - Strategic planning: Plan approach before execution (always enabled)
    """

    def __init__(self, agent: "Agent"):
        """Initialize metacognition for an agent.

        Args:
            agent: The agent this metacognition belongs to
        """
        self.agent = agent
        self.agent_id = agent.id

        # Config
        self.config = MetacognitionConfig(agent.id)

        # Token awareness
        self._tokens: TokenAwareness = get_token_awareness()

        # Progress tracking (centralized in regulation/progress.py)
        self._progress: ProgressTracker = get_progress_tracker()
        self._current_session_id: Optional[str] = None

        # Per-agent tracking state (for telemetry display only)
        self._tool_call_count: int = 0
        self._iteration_count: int = 0

        # Strategic planning
        self.planner = Planner(agent)

        # Logger
        self._logger = get_logger(f"agents/{agent.id}/metacognition")

    # ============== Token Awareness ==============

    def get_agent_state(self) -> AgentState:
        """Get the current state of this agent.

        Returns:
            AgentState enum: ENABLED, DISABLED, or PAUSED
        """
        return self._tokens.get_agent_state(self.agent_id)

    def is_enabled(self) -> bool:
        """Check if this agent is enabled (can run)."""
        return self.get_agent_state() == AgentState.ENABLED

    def is_paused(self) -> bool:
        """Check if this agent is paused (due to threshold breach)."""
        return self.get_agent_state() == AgentState.PAUSED

    def enable(self):
        """Enable this agent (resume from paused or disabled state)."""
        self._tokens.enable_agent(self.agent_id)

    def disable(self):
        """Disable this agent."""
        self._tokens.disable_agent(self.agent_id)

    def resume(self):
        """Resume this agent if paused."""
        self._tokens.enable_agent(self.agent_id)

    def get_token_usage(self) -> dict:
        """Get token usage statistics for this agent.

        Returns:
            Dict with input, output token counts and budget info
        """
        return self._tokens.get_agent_usage(self.agent_id)

    def get_pause_info(self) -> dict:
        """Get pause information for this agent."""
        return self._tokens.get_pause_info(self.agent_id)

    # ============== Action Tracking ==============

    def record_tool_call(self, tool_name: str, tool_input: dict):
        """Record a tool call for telemetry and stuck detection.

        Args:
            tool_name: Name of the tool called
            tool_input: Input parameters to the tool

        Note: If a work session is active, this records to ProgressTracker
        which may raise ProgressLimitExceeded if stuck pattern detected.
        """
        self._tool_call_count += 1

        # Record to progress tracker session if active
        if self._current_session_id:
            # Serialize input for comparison
            input_str = json.dumps(tool_input, sort_keys=True) if tool_input else ""
            self._progress.record_tool_call(self._current_session_id, tool_name, input_str)

    def get_tool_call_count(self) -> int:
        """Get the current tool call count for this iteration."""
        return self._tool_call_count

    def reset_iteration(self):
        """Reset per-iteration tracking state."""
        self._tool_call_count = 0
        self._iteration_count += 1

    def reset_work_cycle(self):
        """Reset tracking state for a new work cycle.

        Note: This is kept for backwards compatibility but session management
        is now handled by start_work_session/end_work_session.
        """
        self._tool_call_count = 0
        self._iteration_count = 0

    # ============== Progress Awareness (delegated to ProgressTracker) ==============

    def start_work_session(self, session_type: str = "work_cycle") -> str:
        """Start a progress tracking session for this work cycle.

        Args:
            session_type: Type of session for logging

        Returns:
            Session ID for tracking
        """
        self._current_session_id = self._progress.start_session(
            agent_id=self.agent_id,
            session_type=session_type
        )
        return self._current_session_id

    def end_work_session(self) -> Optional[dict]:
        """End the current progress tracking session.

        Returns:
            Final session stats, or None if no session active
        """
        if not self._current_session_id:
            return None

        stats = self._progress.end_session(self._current_session_id)
        self._current_session_id = None
        return stats

    def check_stuck(self) -> Optional[str]:
        """Check if the agent appears stuck.

        Delegates to ProgressTracker if a session is active.

        Returns:
            Reason string if stuck, None if making progress
        """
        if not self._current_session_id:
            return None
        return self._progress.check_stuck(self._current_session_id)

    def should_check_progress(self) -> bool:
        """Check if it's time for an LLM progress check.

        Delegates to ProgressTracker if a session is active.
        """
        if not self._current_session_id:
            return False
        return self._progress.should_check_progress(self._current_session_id)

    def get_activity_summary(self) -> dict:
        """Get recent activity summary for progress check.

        Delegates to ProgressTracker if a session is active.
        """
        if not self._current_session_id:
            return {}
        return self._progress.get_recent_activity_summary(self._current_session_id)

    def mark_progress_checked(self):
        """Mark that progress was checked this iteration.

        Delegates to ProgressTracker if a session is active.
        """
        if self._current_session_id:
            self._progress.mark_progress_checked(self._current_session_id)

    def increment_iteration(self) -> int:
        """Increment iteration count and check limits.

        Called at the start of each work cycle iteration to enforce
        max iteration limits.

        Returns:
            Current iteration count

        Raises:
            ProgressLimitExceeded: If max iterations exceeded
        """
        self._iteration_count += 1
        if self._current_session_id:
            return self._progress.increment(self._current_session_id)
        return self._iteration_count

    def get_current_session_id(self) -> Optional[str]:
        """Get the current progress tracking session ID."""
        return self._current_session_id

    # ============== Planning ==============

    def should_plan(self, topic: dict) -> bool:
        """Planning is always enabled for efficiency."""
        return True

    # ============== Efficiency ==============

    def should_defer_consolidation(self) -> bool:
        """Consolidation append is deferred until end of work cycle."""
        return True

    # ============== Combined Status ==============

    def get_status(self) -> dict:
        """Get complete metacognition status for this agent.

        Returns:
            Dict with all metacognition state
        """
        # Get progress info from session if active
        progress_info = {}
        if self._current_session_id:
            session_progress = self._progress.get_progress(self._current_session_id)
            if session_progress:
                progress_info = {
                    "session_id": session_progress["session_id"],
                    "tool_call_count": session_progress["tool_call_count"],
                    "is_stuck": session_progress["is_stuck"],
                    "stuck_reason": session_progress["stuck_reason"]
                }
        else:
            progress_info = {
                "session_id": None,
                "tool_call_count": self._tool_call_count,
                "is_stuck": False,
                "stuck_reason": None
            }

        return {
            "agent_id": self.agent_id,
            "state": self.get_agent_state().value,
            "token_usage": self.get_token_usage(),
            "action": {
                "tool_call_count": self._tool_call_count,
                "iteration_count": self._iteration_count
            },
            "progress": progress_info,
            "paused": self.is_paused(),
            "pause_info": self.get_pause_info()
        }

    def get_progress_context(self) -> dict:
        """Get progress context for injecting into continue prompt.

        Returns:
            Dict with progress info for prompt injection
        """
        stuck_reason = self.check_stuck()
        return {
            "iteration": self._iteration_count,
            "tool_calls_this_cycle": self._tool_call_count,
            "is_stuck": stuck_reason is not None,
            "stuck_warning": stuck_reason
        }

    # ============== Logging ==============

    def log(self, event: str, details: dict = None):
        """Log a metacognition event.

        Args:
            event: Event type
            details: Optional event details
        """
        entry = {"event": event, "agent_id": self.agent_id}
        if details:
            entry["details"] = details
        self._logger.info(entry)

    # ============== Config ==============

    def invalidate_config(self):
        """Invalidate cached configuration."""
        self.config.invalidate()
        self._tokens.invalidate_config()
