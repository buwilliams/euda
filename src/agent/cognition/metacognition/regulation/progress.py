"""
Progress Tracking - Detect stuck/spinning behavior in agent sessions.

This module tracks iteration counts within sessions (like RLM) and detects
when an agent appears to be spinning without making progress. It complements
token awareness by catching loops that don't necessarily burn tokens quickly.

All loop detection is centralized here:
- Iteration limits (max iterations per session)
- Recursion depth limits
- Stuck pattern detection (repeated identical tool calls)
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from ....logger import get_logger
from .incidents import (
    get_incident_tracker,
    IncidentType,
    IncidentSeverity
)


# Default limits - can be overridden per-session
DEFAULT_MAX_ITERATIONS = 20
DEFAULT_MAX_RECURSION_DEPTH = 3
DEFAULT_STUCK_THRESHOLD = 5  # Same tool+input N times = stuck
DEFAULT_TOOL_HISTORY_LIMIT = 100  # Max tool calls to track per session


@dataclass
class ToolCall:
    """A recorded tool call."""
    tool: str
    input: str  # JSON-serialized input for comparison


@dataclass
class SessionProgress:
    """Tracks progress within a single session."""
    session_id: str
    agent_id: str
    iteration_count: int = 0
    recursion_depth: int = 0
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    max_recursion_depth: int = DEFAULT_MAX_RECURSION_DEPTH
    stuck_threshold: int = DEFAULT_STUCK_THRESHOLD
    tool_history: List[ToolCall] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())


class ProgressLimitExceeded(Exception):
    """Raised when a session exceeds iteration or recursion limits."""

    def __init__(self, agent_id: str, session_id: str, reason: str):
        self.agent_id = agent_id
        self.session_id = session_id
        self.reason = reason
        super().__init__(f"Session {session_id} for agent {agent_id}: {reason}")


class ProgressTracker:
    """Tracks progress across agent sessions to detect stuck behavior.

    Provides:
    - Per-session iteration counting
    - Recursion depth tracking
    - Automatic incident recording when limits exceeded
    - Thread-safe implementation

    Usage:
        tracker = get_progress_tracker()
        session_id = tracker.start_session(agent_id)
        try:
            while working:
                tracker.increment(session_id)  # Raises if limit exceeded
                # ... do work ...
        finally:
            tracker.end_session(session_id)
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._logger = get_logger("system/logs/progress")
        self._sessions: Dict[str, SessionProgress] = {}
        self._session_counter = 0

    def start_session(
        self,
        agent_id: str,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        max_recursion_depth: int = DEFAULT_MAX_RECURSION_DEPTH,
        stuck_threshold: int = DEFAULT_STUCK_THRESHOLD,
        session_type: str = "generic"
    ) -> str:
        """Start tracking a new session.

        Args:
            agent_id: ID of the agent running the session
            max_iterations: Maximum allowed iterations (default 20)
            max_recursion_depth: Maximum recursion depth (default 3)
            stuck_threshold: Number of identical tool calls before stuck (default 5)
            session_type: Type of session for logging (e.g., "rlm", "work_cycle")

        Returns:
            Session ID for tracking
        """
        with self._lock:
            self._session_counter += 1
            session_id = f"{agent_id}-{session_type}-{self._session_counter}"

            self._sessions[session_id] = SessionProgress(
                session_id=session_id,
                agent_id=agent_id,
                max_iterations=max_iterations,
                max_recursion_depth=max_recursion_depth,
                stuck_threshold=stuck_threshold
            )

            self._logger.debug({
                "event": "session_started",
                "session_id": session_id,
                "agent_id": agent_id,
                "session_type": session_type,
                "max_iterations": max_iterations,
                "stuck_threshold": stuck_threshold
            })

            return session_id

    def increment(self, session_id: str) -> int:
        """Increment iteration count and check limits.

        Args:
            session_id: Session to increment

        Returns:
            Current iteration count

        Raises:
            ProgressLimitExceeded: If max iterations exceeded
            KeyError: If session not found
        """
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session {session_id} not found")

            session = self._sessions[session_id]
            session.iteration_count += 1
            session.last_activity = datetime.now().isoformat()

            if session.iteration_count > session.max_iterations:
                self._record_limit_exceeded(session, "iteration")
                raise ProgressLimitExceeded(
                    session.agent_id,
                    session_id,
                    f"max iterations exceeded ({session.iteration_count}/{session.max_iterations})"
                )

            return session.iteration_count

    def record_tool_call(self, session_id: str, tool_name: str, tool_input: str):
        """Record a tool call for stuck pattern detection.

        Args:
            session_id: Session to record for
            tool_name: Name of the tool called
            tool_input: JSON-serialized input (for comparison)

        Raises:
            ProgressLimitExceeded: If stuck pattern detected
            KeyError: If session not found
        """
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session {session_id} not found")

            session = self._sessions[session_id]
            session.tool_history.append(ToolCall(tool=tool_name, input=tool_input))
            session.last_activity = datetime.now().isoformat()

            # Keep history bounded
            if len(session.tool_history) > DEFAULT_TOOL_HISTORY_LIMIT:
                session.tool_history = session.tool_history[-DEFAULT_TOOL_HISTORY_LIMIT // 2:]

            # Check for stuck pattern
            stuck_reason = self._check_stuck_pattern(session)
            if stuck_reason:
                self._record_stuck_detected(session, stuck_reason)
                raise ProgressLimitExceeded(
                    session.agent_id,
                    session_id,
                    stuck_reason
                )

    def check_stuck(self, session_id: str) -> Optional[str]:
        """Check if a session appears stuck without raising.

        Args:
            session_id: Session to check

        Returns:
            Reason string if stuck, None if making progress
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            return self._check_stuck_pattern(session)

    def _check_stuck_pattern(self, session: SessionProgress) -> Optional[str]:
        """Check for stuck patterns in tool history.

        Args:
            session: Session to check

        Returns:
            Reason string if stuck, None if making progress
        """
        threshold = session.stuck_threshold
        if len(session.tool_history) < threshold:
            return None

        # Check for same tool called N times with identical inputs
        recent = session.tool_history[-threshold:]
        first = recent[0]
        if all(t.tool == first.tool and t.input == first.input for t in recent):
            return f"Same tool '{first.tool}' called {threshold} times with identical inputs"

        return None

    def _record_stuck_detected(self, session: SessionProgress, reason: str):
        """Record an incident when stuck pattern detected."""
        get_incident_tracker().record(
            agent_id=session.agent_id,
            incident_type=IncidentType.ITERATION_LIMIT_EXCEEDED,  # Reuse for now
            reason=f"Stuck pattern detected: {reason}",
            severity=IncidentSeverity.WARNING,
            details={
                "session_id": session.session_id,
                "iteration_count": session.iteration_count,
                "tool_history_length": len(session.tool_history),
                "stuck_threshold": session.stuck_threshold
            }
        )

        self._logger.warn({
            "event": "stuck_pattern_detected",
            "session_id": session.session_id,
            "agent_id": session.agent_id,
            "reason": reason
        })

    def enter_recursion(self, session_id: str) -> int:
        """Enter a recursion level and check depth limit.

        Args:
            session_id: Session entering recursion

        Returns:
            Current recursion depth

        Raises:
            ProgressLimitExceeded: If max recursion depth exceeded
            KeyError: If session not found
        """
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session {session_id} not found")

            session = self._sessions[session_id]
            session.recursion_depth += 1

            if session.recursion_depth > session.max_recursion_depth:
                self._record_limit_exceeded(session, "recursion")
                raise ProgressLimitExceeded(
                    session.agent_id,
                    session_id,
                    f"max recursion depth exceeded ({session.recursion_depth}/{session.max_recursion_depth})"
                )

            return session.recursion_depth

    def exit_recursion(self, session_id: str) -> int:
        """Exit a recursion level.

        Args:
            session_id: Session exiting recursion

        Returns:
            Current recursion depth after exit
        """
        with self._lock:
            if session_id not in self._sessions:
                return 0

            session = self._sessions[session_id]
            session.recursion_depth = max(0, session.recursion_depth - 1)
            return session.recursion_depth

    def get_progress(self, session_id: str) -> Optional[dict]:
        """Get current progress for a session.

        Args:
            session_id: Session to query

        Returns:
            Dict with iteration_count, recursion_depth, tool_history, limits, or None if not found
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            stuck_reason = self._check_stuck_pattern(session)
            return {
                "session_id": session.session_id,
                "agent_id": session.agent_id,
                "iteration_count": session.iteration_count,
                "recursion_depth": session.recursion_depth,
                "tool_call_count": len(session.tool_history),
                "max_iterations": session.max_iterations,
                "max_recursion_depth": session.max_recursion_depth,
                "stuck_threshold": session.stuck_threshold,
                "is_stuck": stuck_reason is not None,
                "stuck_reason": stuck_reason,
                "started_at": session.started_at,
                "last_activity": session.last_activity
            }

    def end_session(self, session_id: str) -> Optional[dict]:
        """End a session and return final stats.

        Args:
            session_id: Session to end

        Returns:
            Final session stats, or None if session not found
        """
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if not session:
                return None

            stats = {
                "session_id": session.session_id,
                "agent_id": session.agent_id,
                "total_iterations": session.iteration_count,
                "total_tool_calls": len(session.tool_history),
                "max_recursion_reached": session.recursion_depth,
                "started_at": session.started_at,
                "ended_at": datetime.now().isoformat()
            }

            self._logger.debug({
                "event": "session_ended",
                **stats
            })

            return stats

    def _record_limit_exceeded(self, session: SessionProgress, limit_type: str):
        """Record an incident when a limit is exceeded."""
        incident_type = (
            IncidentType.ITERATION_LIMIT_EXCEEDED
            if limit_type == "iteration"
            else IncidentType.RECURSION_LIMIT_EXCEEDED
        )

        get_incident_tracker().record(
            agent_id=session.agent_id,
            incident_type=incident_type,
            reason=f"{limit_type} limit exceeded in session {session.session_id}",
            severity=IncidentSeverity.WARNING,
            details={
                "session_id": session.session_id,
                "iteration_count": session.iteration_count,
                "recursion_depth": session.recursion_depth,
                "max_iterations": session.max_iterations,
                "max_recursion_depth": session.max_recursion_depth
            }
        )

        self._logger.warn({
            "event": f"{limit_type}_limit_exceeded",
            "session_id": session.session_id,
            "agent_id": session.agent_id,
            "count": session.iteration_count if limit_type == "iteration" else session.recursion_depth,
            "limit": session.max_iterations if limit_type == "iteration" else session.max_recursion_depth
        })


# Singleton instance
_progress_tracker: Optional[ProgressTracker] = None
_progress_tracker_lock = threading.Lock()


def get_progress_tracker() -> ProgressTracker:
    """Get the global ProgressTracker instance."""
    global _progress_tracker
    with _progress_tracker_lock:
        if _progress_tracker is None:
            _progress_tracker = ProgressTracker()
        return _progress_tracker
