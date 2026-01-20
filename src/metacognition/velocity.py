"""
Velocity Awareness - Controls LLM API call frequency and detects runaway agents.

Provides:
- Rolling window rate limiting (global across all agents)
- Queue-based throttling for controlled pacing
- Runaway agent detection via call velocity monitoring
- Event logging for rate limit events

This module was migrated from src/rate_limiter.py as part of the
metacognition consolidation.
"""

import json
import queue
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Set

from ..logger import get_logger
from ..events import emit_ui_event


DATA_DIR = Path(__file__).parent.parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"

# Cached config for rate limiting
_rate_limiting_config_cache: dict = None
_rate_limiting_config_mtime: float = 0


def _load_rate_limiting_config() -> dict:
    """Load rate limiting config from llm.rate_limiting with caching."""
    global _rate_limiting_config_cache, _rate_limiting_config_mtime

    try:
        current_mtime = CONFIG_PATH.stat().st_mtime
        if _rate_limiting_config_cache is not None and current_mtime == _rate_limiting_config_mtime:
            return _rate_limiting_config_cache

        with open(CONFIG_PATH) as f:
            config = json.load(f)

        _rate_limiting_config_cache = config.get("llm", {}).get("rate_limiting", {})
        _rate_limiting_config_mtime = current_mtime
        return _rate_limiting_config_cache
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def invalidate_rate_limiting_config():
    """Invalidate the rate limiting config cache."""
    global _rate_limiting_config_cache, _rate_limiting_config_mtime
    _rate_limiting_config_cache = None
    _rate_limiting_config_mtime = 0


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded and call cannot proceed."""
    pass


class AgentPausedError(Exception):
    """Raised when an agent is paused due to runaway detection."""

    def __init__(self, agent_id: str, reason: str):
        self.agent_id = agent_id
        self.reason = reason
        super().__init__(f"Agent {agent_id} is paused: {reason}")


class VelocityTracker:
    """Global velocity tracker for LLM API calls.

    Thread-safe implementation that provides:
    - Rolling window rate limiting
    - Queue-based throttling (when enabled)
    - Runaway agent detection via call velocity spikes

    This is the metacognition component for velocity awareness.
    """

    def __init__(self):
        self._lock = threading.RLock()

        # Rolling window tracking (global)
        self._call_timestamps: deque = deque()

        # Per-agent call history for runaway detection
        self._agent_call_history: Dict[str, deque] = {}

        # Per-agent job completion history for progress tracking
        self._agent_completion_history: Dict[str, deque] = {}

        # Paused agents
        self._paused_agents: Set[str] = set()
        self._pause_reasons: Dict[str, str] = {}
        self._pause_timestamps: Dict[str, str] = {}

        # Throttle queue
        self._throttle_queue: queue.Queue = queue.Queue()
        self._throttle_thread: Optional[threading.Thread] = None
        self._throttle_running = False

        # Logger
        self._logger = get_logger("system/logs/rate-limiting")

    def _get_velocity_config(self) -> dict:
        """Get rate limiting configuration from llm.rate_limiting."""
        return _load_rate_limiting_config()

    def _get_rolling_window_config(self) -> dict:
        """Get rolling window configuration."""
        config = self._get_velocity_config()
        rolling_window = config.get("rolling_window", {})
        return {
            "max_calls": rolling_window.get("max_calls", 30),
            "window_seconds": rolling_window.get("window_seconds", 60)
        }

    def _get_runaway_config(self) -> dict:
        """Get runaway detection configuration."""
        config = self._get_velocity_config()
        runaway = config.get("runaway_detection", {})
        return {
            "enabled": runaway.get("enabled", True),
            "baseline_window_minutes": runaway.get("baseline_window_minutes", 60),
            "spike_multiplier": runaway.get("spike_multiplier", 5.0),
            "min_baseline_calls": runaway.get("min_baseline_calls", 5),
            "min_spike_rate": runaway.get("min_spike_rate", 5),
            "pause_cooldown_minutes": runaway.get("pause_cooldown_minutes", 5)
        }

    def is_enabled(self) -> bool:
        """Check if velocity tracking is enabled."""
        config = self._get_velocity_config()
        return config.get("enabled", True)

    def acquire(self, agent_id: Optional[str] = None, job_id: Optional[str] = None) -> bool:
        """Acquire permission to make an API call.

        This is called BEFORE making an LLM API call. It uses optimistic
        booking to prevent TOCTOU races - the slot is booked immediately
        upon passing checks, before the actual API call is made.

        Args:
            agent_id: ID of the calling agent
            job_id: ID of the job being worked on

        Returns:
            True if call can proceed

        Raises:
            AgentPausedError: If agent is paused due to runaway detection
            RateLimitExceeded: If rate limit exceeded and cannot proceed
        """
        if not self.is_enabled():
            return True

        with self._lock:
            # Check if agent is paused
            if agent_id and agent_id in self._paused_agents:
                raise AgentPausedError(agent_id, self._pause_reasons.get(agent_id, "unknown"))

            # Check runaway detection BEFORE allowing call
            if agent_id and self._check_runaway(agent_id):
                self._pause_agent(agent_id, "runaway_detected", job_id)
                raise AgentPausedError(agent_id, "runaway_detected")

            # Check rolling window
            if not self._check_rolling_window():
                self._log_event("rate_limit_hit", {
                    "agent_id": agent_id,
                    "job_id": job_id,
                    "reason": "rolling_window_exceeded"
                })
                raise RateLimitExceeded("Rolling window rate limit exceeded")

            # OPTIMISTIC BOOKING: Book the slot NOW, before the API call.
            # This prevents TOCTOU races where multiple threads pass the check
            # before any of them record their call.
            self._call_timestamps.append(time.time())

            return True

    def record_call(self, agent_id: Optional[str] = None, job_id: Optional[str] = None):
        """Record a completed API call for per-agent tracking.

        This is called AFTER a successful LLM API call to update
        per-agent history for runaway detection and statistics.

        Note: The global rolling window slot is already booked in acquire()
        via optimistic booking. This method only tracks per-agent history.

        Args:
            agent_id: ID of the calling agent
            job_id: ID of the job being worked on
        """
        if not self.is_enabled():
            return

        now = time.time()

        with self._lock:
            # Note: Global _call_timestamps is already updated in acquire()
            # via optimistic booking. Here we only track per-agent history.

            # Add to per-agent history for runaway detection
            if agent_id:
                if agent_id not in self._agent_call_history:
                    self._agent_call_history[agent_id] = deque()
                self._agent_call_history[agent_id].append(now)

            # Cleanup old entries periodically
            self._cleanup_old_entries()

    def record_completion(self, agent_id: str, job_id: Optional[str] = None):
        """Record a job completion for progress tracking.

        This helps distinguish legitimate batch processing (completing jobs)
        from runaway behavior (making calls without progress).

        Args:
            agent_id: ID of the agent that completed the job
            job_id: ID of the completed job (optional, for logging)
        """
        if not self.is_enabled():
            return

        now = time.time()

        with self._lock:
            if agent_id not in self._agent_completion_history:
                self._agent_completion_history[agent_id] = deque()
            self._agent_completion_history[agent_id].append(now)

    def _check_rolling_window(self) -> bool:
        """Check if within rolling window limits.

        Returns:
            True if within limits, False if exceeded
        """
        config = self._get_rolling_window_config()
        max_calls = config.get("max_calls", 30)
        window_seconds = config.get("window_seconds", 60)

        now = time.time()
        cutoff = now - window_seconds

        # Count calls in window
        calls_in_window = sum(1 for ts in self._call_timestamps if ts >= cutoff)

        return calls_in_window < max_calls

    def get_utilization(self) -> dict:
        """Get current rate limit utilization for load-based pacing.

        Returns:
            Dict with:
            - calls_in_window: current call count
            - max_calls: configured limit
            - utilization: percentage (0.0 to 1.0+)
            - recommended_delay: seconds to wait based on load (0 if low utilization)
        """
        config = self._get_rolling_window_config()
        max_calls = config.get("max_calls", 30)
        window_seconds = config.get("window_seconds", 60)

        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            calls_in_window = sum(1 for ts in self._call_timestamps if ts >= cutoff)

        utilization = calls_in_window / max_calls if max_calls > 0 else 0

        # Calculate recommended delay based on utilization
        # < 50% → no delay (plenty of headroom)
        # 50-80% → 1-3 second delay (moderate load)
        # > 80% → 3-10 second delay (high load, need to pace)
        if utilization < 0.5:
            delay = 0
        elif utilization < 0.8:
            # Linear scale from 1s at 50% to 3s at 80%
            delay = 1 + (utilization - 0.5) * (2 / 0.3)
        else:
            # Linear scale from 3s at 80% to 10s at 100%+
            delay = 3 + (utilization - 0.8) * (7 / 0.2)
            delay = min(delay, 15)  # Cap at 15 seconds

        return {
            "calls_in_window": calls_in_window,
            "max_calls": max_calls,
            "window_seconds": window_seconds,
            "utilization": round(utilization, 2),
            "recommended_delay": round(delay, 1)
        }

    def _check_runaway(self, agent_id: str) -> bool:
        """Check for runaway agent behavior.

        Algorithm:
        1. Check if agent is making progress (completing jobs) - if so, not runaway
        2. Calculate baseline: calls/minute over last baseline_window_minutes
        3. Calculate current rate: calls in last 60 seconds
        4. Only flag as runaway if ALL:
           - No recent job completions (no progress)
           - current_rate > baseline * spike_multiplier
           - current_rate >= min_spike_rate (absolute threshold)

        Returns:
            True if runaway detected, False otherwise
        """
        # Exempt interactive agents - they're human-driven, not autonomous
        # The 'user' and 'chat' agents naturally have bursty behavior from conversations
        if agent_id in ("user", "chat"):
            return False

        config = self._get_runaway_config()
        if not config.get("enabled", True):
            return False

        baseline_minutes = config.get("baseline_window_minutes", 60)
        spike_mult = config.get("spike_multiplier", 5.0)
        min_calls = config.get("min_baseline_calls", 5)
        min_spike_rate = config.get("min_spike_rate", 5)

        history = self._agent_call_history.get(agent_id)
        if not history:
            return False

        now = time.time()
        one_minute_ago = now - 60
        five_minutes_ago = now - 300
        baseline_start = now - (baseline_minutes * 60)

        # Check for progress: job completions in last 5 minutes
        # If agent is completing jobs, it's doing legitimate work, not runaway
        completion_history = self._agent_completion_history.get(agent_id, deque())
        recent_completions = sum(1 for ts in completion_history if ts >= five_minutes_ago)
        if recent_completions > 0:
            # Agent is making progress - not runaway
            return False

        # Count calls in baseline window and last minute
        baseline_calls = sum(1 for ts in history if ts >= baseline_start)
        recent_calls = sum(1 for ts in history if ts >= one_minute_ago)

        # Not enough history to detect
        if baseline_calls < min_calls:
            return False

        # Calculate rates
        baseline_rate = baseline_calls / baseline_minutes  # calls per minute
        current_rate = recent_calls  # calls in last minute

        # Only trigger runaway if current rate exceeds BOTH:
        # 1. The spike threshold (baseline * multiplier)
        # 2. The absolute minimum rate (to avoid false positives from low baselines)
        if current_rate >= min_spike_rate and current_rate > baseline_rate * spike_mult:
            return True

        return False

    def _pause_agent(self, agent_id: str, reason: str, job_id: Optional[str] = None):
        """Pause an agent due to runaway detection."""
        self._paused_agents.add(agent_id)
        self._pause_reasons[agent_id] = reason
        self._pause_timestamps[agent_id] = datetime.now().isoformat()

        # Get detection stats for logging
        history = self._agent_call_history.get(agent_id, deque())
        config = self._get_runaway_config()
        baseline_minutes = config.get("baseline_window_minutes", 60)

        now = time.time()
        one_minute_ago = now - 60
        baseline_start = now - (baseline_minutes * 60)

        baseline_calls = sum(1 for ts in history if ts >= baseline_start)
        recent_calls = sum(1 for ts in history if ts >= one_minute_ago)
        baseline_rate = baseline_calls / baseline_minutes if baseline_minutes > 0 else 0

        self._log_event("agent_paused", {
            "agent_id": agent_id,
            "job_id": job_id,
            "reason": reason,
            "baseline_rate": round(baseline_rate, 2),
            "current_rate": recent_calls,
            "spike_multiplier": config.get("spike_multiplier", 5.0)
        })

        # Emit SSE event for real-time UI updates
        emit_ui_event("agent:paused", {
            "agent_id": agent_id,
            "reason": reason,
            "timestamp": self._pause_timestamps[agent_id]
        })

        print(f"[METACOGNITION] Agent '{agent_id}' paused: {reason} "
              f"(current: {recent_calls}/min, baseline: {baseline_rate:.1f}/min)")

    def is_agent_paused(self, agent_id: str) -> bool:
        """Check if an agent is paused."""
        with self._lock:
            if agent_id not in self._paused_agents:
                return False

            # Check if cooldown has expired
            remaining = self._get_remaining_cooldown_seconds(agent_id)
            if remaining <= 0:
                # Auto-resume
                self._auto_resume_agent(agent_id)
                return False

            return True

    def _get_remaining_cooldown_seconds(self, agent_id: str) -> int:
        """Get remaining cooldown time in seconds. Must be called with lock held."""
        pause_timestamp = self._pause_timestamps.get(agent_id)
        if not pause_timestamp:
            return 0

        config = self._get_runaway_config()
        cooldown_minutes = config.get("pause_cooldown_minutes", 5)

        try:
            pause_time = datetime.fromisoformat(pause_timestamp)
            elapsed = (datetime.now() - pause_time).total_seconds()
            remaining = (cooldown_minutes * 60) - elapsed
            return max(0, int(remaining))
        except ValueError:
            return 0

    def _auto_resume_agent(self, agent_id: str):
        """Auto-resume an agent after cooldown. Must be called with lock held."""
        pause_timestamp = self._pause_timestamps.get(agent_id)

        self._paused_agents.discard(agent_id)
        self._pause_reasons.pop(agent_id, None)
        self._pause_timestamps.pop(agent_id, None)

        duration_minutes = None
        if pause_timestamp:
            try:
                pause_time = datetime.fromisoformat(pause_timestamp)
                duration = datetime.now() - pause_time
                duration_minutes = round(duration.total_seconds() / 60, 1)
            except ValueError:
                pass

        self._log_event("agent_resumed", {
            "agent_id": agent_id,
            "resumed_by": "cooldown",
            "paused_duration_minutes": duration_minutes
        })

        # Emit SSE event for real-time UI updates
        emit_ui_event("agent:resumed", {
            "agent_id": agent_id
        })

        print(f"[METACOGNITION] Agent '{agent_id}' auto-resumed after cooldown")

    def get_pause_info(self, agent_id: str) -> dict:
        """Get pause information for an agent.

        Returns:
            Dict with is_paused, reason, remaining_seconds
        """
        with self._lock:
            if agent_id not in self._paused_agents:
                return {"is_paused": False}

            remaining = self._get_remaining_cooldown_seconds(agent_id)
            if remaining <= 0:
                self._auto_resume_agent(agent_id)
                return {"is_paused": False}

            return {
                "is_paused": True,
                "reason": self._pause_reasons.get(agent_id, "unknown"),
                "remaining_seconds": remaining
            }

    def resume_agent(self, agent_id: str):
        """Resume a paused agent.

        Args:
            agent_id: ID of the agent to resume
        """
        with self._lock:
            if agent_id in self._paused_agents:
                pause_timestamp = self._pause_timestamps.get(agent_id)

                self._paused_agents.discard(agent_id)
                self._pause_reasons.pop(agent_id, None)
                self._pause_timestamps.pop(agent_id, None)

                # Calculate pause duration
                duration_minutes = None
                if pause_timestamp:
                    try:
                        pause_time = datetime.fromisoformat(pause_timestamp)
                        duration = datetime.now() - pause_time
                        duration_minutes = round(duration.total_seconds() / 60, 1)
                    except ValueError:
                        pass

                self._log_event("agent_resumed", {
                    "agent_id": agent_id,
                    "resumed_by": "user",
                    "paused_duration_minutes": duration_minutes
                })

                # Emit SSE event for real-time UI updates
                emit_ui_event("agent:resumed", {
                    "agent_id": agent_id
                })

                print(f"[METACOGNITION] Agent '{agent_id}' resumed")

    def get_status(self) -> dict:
        """Get current velocity tracking status for UI.

        Returns:
            Dict with current status information
        """
        with self._lock:
            config = self._get_velocity_config()
            rolling_config = self._get_rolling_window_config()
            runaway_config = self._get_runaway_config()

            now = time.time()
            window_seconds = rolling_config.get("window_seconds", 60)
            cutoff = now - window_seconds

            calls_in_window = sum(1 for ts in self._call_timestamps if ts >= cutoff)

            return {
                "enabled": config.get("enabled", True),
                "rolling_window": {
                    "max_calls": rolling_config.get("max_calls", 30),
                    "window_seconds": window_seconds,
                    "current_calls": calls_in_window
                },
                "runaway_detection": {
                    "enabled": runaway_config.get("enabled", True),
                    "spike_multiplier": runaway_config.get("spike_multiplier", 5.0)
                },
                "paused_agents": list(self._paused_agents),
                "pause_details": {
                    agent_id: {
                        "reason": self._pause_reasons.get(agent_id),
                        "timestamp": self._pause_timestamps.get(agent_id)
                    }
                    for agent_id in self._paused_agents
                }
            }

    def get_agent_stats(self, agent_id: str) -> dict:
        """Get velocity stats for a specific agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Dict with agent-specific stats
        """
        with self._lock:
            history = self._agent_call_history.get(agent_id, deque())

            now = time.time()
            one_minute_ago = now - 60
            one_hour_ago = now - 3600

            calls_last_minute = sum(1 for ts in history if ts >= one_minute_ago)
            calls_last_hour = sum(1 for ts in history if ts >= one_hour_ago)

            return {
                "agent_id": agent_id,
                "calls_last_minute": calls_last_minute,
                "calls_last_hour": calls_last_hour,
                "is_paused": agent_id in self._paused_agents,
                "pause_reason": self._pause_reasons.get(agent_id),
                "pause_timestamp": self._pause_timestamps.get(agent_id)
            }

    def _cleanup_old_entries(self):
        """Remove old entries from tracking data structures."""
        config = self._get_runaway_config()
        baseline_minutes = config.get("baseline_window_minutes", 60)

        # Keep entries for baseline window + buffer
        max_age = (baseline_minutes + 10) * 60
        cutoff = time.time() - max_age

        # Clean global timestamps
        while self._call_timestamps and self._call_timestamps[0] < cutoff:
            self._call_timestamps.popleft()

        # Clean per-agent call history
        for agent_id in list(self._agent_call_history.keys()):
            history = self._agent_call_history[agent_id]
            while history and history[0] < cutoff:
                history.popleft()

            # Remove empty histories
            if not history:
                del self._agent_call_history[agent_id]

        # Clean per-agent completion history
        for agent_id in list(self._agent_completion_history.keys()):
            history = self._agent_completion_history[agent_id]
            while history and history[0] < cutoff:
                history.popleft()

            # Remove empty histories
            if not history:
                del self._agent_completion_history[agent_id]

    def _log_event(self, event_type: str, details: dict):
        """Log a velocity/rate limiting event."""
        self._logger.info({
            "event": event_type,
            **details
        })

    def invalidate_config(self):
        """Invalidate cached config. Call when settings change."""
        invalidate_rate_limiting_config()


# Singleton instance
_velocity_tracker: Optional[VelocityTracker] = None
_velocity_tracker_lock = threading.Lock()


def get_velocity_tracker() -> VelocityTracker:
    """Get the global velocity tracker instance."""
    global _velocity_tracker
    with _velocity_tracker_lock:
        if _velocity_tracker is None:
            _velocity_tracker = VelocityTracker()
        return _velocity_tracker
