"""
Rate Limiter - Controls LLM API call frequency and detects runaway agents.

Provides:
- Rolling window rate limiting (global across all agents)
- Queue-based throttling for controlled pacing
- Runaway agent detection via call velocity monitoring
- Event logging for rate limit events
"""

import json
import queue
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Set

from .logger import get_logger


DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded and call cannot proceed."""
    pass


class AgentPausedError(Exception):
    """Raised when an agent is paused due to runaway detection."""

    def __init__(self, agent_id: str, reason: str):
        self.agent_id = agent_id
        self.reason = reason
        super().__init__(f"Agent {agent_id} is paused: {reason}")


class RateLimiter:
    """Global rate limiter for LLM API calls.

    Thread-safe implementation that provides:
    - Rolling window rate limiting
    - Queue-based throttling (when enabled)
    - Runaway agent detection via call velocity spikes
    """

    def __init__(self):
        self._lock = threading.RLock()

        # Rolling window tracking (global)
        self._call_timestamps: deque = deque()

        # Per-agent call history for runaway detection
        self._agent_call_history: Dict[str, deque] = {}

        # Paused agents
        self._paused_agents: Set[str] = set()
        self._pause_reasons: Dict[str, str] = {}
        self._pause_timestamps: Dict[str, str] = {}

        # Throttle queue
        self._throttle_queue: queue.Queue = queue.Queue()
        self._throttle_thread: Optional[threading.Thread] = None
        self._throttle_running = False

        # Config caching
        self._config_cache: Optional[dict] = None
        self._config_mtime: float = 0

        # Logger
        self._logger = get_logger("system/logs/rate-limiting")

    def _load_config(self) -> dict:
        """Load rate limiting config with file mtime caching."""
        try:
            current_mtime = CONFIG_PATH.stat().st_mtime
            if self._config_cache is not None and current_mtime == self._config_mtime:
                return self._config_cache

            with open(CONFIG_PATH) as f:
                config = json.load(f)

            self._config_cache = config.get("llm", {}).get("rate_limiting", {})
            self._config_mtime = current_mtime
            return self._config_cache
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _get_rolling_window_config(self) -> dict:
        """Get rolling window configuration."""
        config = self._load_config()
        return config.get("rolling_window", {
            "max_calls": 30,
            "window_seconds": 60
        })

    def _get_throttle_config(self) -> dict:
        """Get throttle configuration."""
        config = self._load_config()
        return config.get("throttle", {
            "enabled": False,
            "calls_per_minute": 10,
            "queue_max_size": 100
        })

    def _get_runaway_config(self) -> dict:
        """Get runaway detection configuration."""
        config = self._load_config()
        return config.get("runaway_detection", {
            "enabled": True,
            "baseline_window_minutes": 60,
            "spike_multiplier": 5.0,
            "min_baseline_calls": 5,
            "min_spike_rate": 5,  # Minimum calls/min before runaway detection triggers
            "pause_cooldown_minutes": 5  # Auto-resume after this many minutes
        })

    def is_enabled(self) -> bool:
        """Check if rate limiting is enabled."""
        config = self._load_config()
        return config.get("enabled", True)

    def acquire(self, agent_id: Optional[str] = None, job_id: Optional[str] = None) -> bool:
        """Acquire permission to make an API call.

        This is called BEFORE making an LLM API call. It may block if
        throttling is enabled and the queue is processing.

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

            # Handle throttling (queue-based)
            throttle_config = self._get_throttle_config()
            if throttle_config.get("enabled", False):
                return self._handle_throttle(agent_id, job_id)

            return True

    def record_call(self, agent_id: Optional[str] = None, job_id: Optional[str] = None):
        """Record a completed API call for tracking.

        This is called AFTER a successful LLM API call to update
        tracking for runaway detection and statistics.

        Args:
            agent_id: ID of the calling agent
            job_id: ID of the job being worked on
        """
        if not self.is_enabled():
            return

        now = time.time()

        with self._lock:
            # Add to global rolling window
            self._call_timestamps.append(now)

            # Add to per-agent history
            if agent_id:
                if agent_id not in self._agent_call_history:
                    self._agent_call_history[agent_id] = deque()
                self._agent_call_history[agent_id].append(now)

            # Cleanup old entries periodically
            self._cleanup_old_entries()

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

    def _check_runaway(self, agent_id: str) -> bool:
        """Check for runaway agent behavior.

        Algorithm:
        1. Calculate baseline: calls/minute over last baseline_window_minutes
        2. Calculate current rate: calls in last 60 seconds
        3. Only flag as runaway if BOTH:
           - current_rate > baseline * spike_multiplier
           - current_rate >= min_spike_rate (absolute threshold)

        Returns:
            True if runaway detected, False otherwise
        """
        config = self._get_runaway_config()
        if not config.get("enabled", True):
            return False

        baseline_minutes = config.get("baseline_window_minutes", 60)
        spike_mult = config.get("spike_multiplier", 5.0)
        min_calls = config.get("min_baseline_calls", 5)
        min_spike_rate = config.get("min_spike_rate", 5)  # Absolute minimum before triggering

        history = self._agent_call_history.get(agent_id)
        if not history:
            return False

        now = time.time()
        one_minute_ago = now - 60
        baseline_start = now - (baseline_minutes * 60)

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

    def _handle_throttle(self, agent_id: Optional[str], job_id: Optional[str]) -> bool:
        """Handle queue-based throttling.

        When throttling is enabled, this enforces a fixed rate of calls
        by adding delays between calls.

        Returns:
            True when ready to proceed (after any necessary delay)
        """
        config = self._get_throttle_config()
        calls_per_minute = config.get("calls_per_minute", 10)

        # Calculate delay needed between calls
        delay_seconds = 60.0 / calls_per_minute

        # Simple delay-based throttling
        # For more sophisticated queue-based throttling, we'd use a background thread
        time.sleep(delay_seconds)

        self._log_event("throttle_delay", {
            "agent_id": agent_id,
            "job_id": job_id,
            "delay_seconds": delay_seconds
        })

        return True

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

        print(f"[RATE LIMITER] Agent '{agent_id}' paused: {reason} "
              f"(current: {recent_calls}/min, baseline: {baseline_rate:.1f}/min)")

    def is_agent_paused(self, agent_id: str) -> bool:
        """Check if an agent is paused. Auto-resumes if cooldown expired."""
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

        print(f"[RATE LIMITER] Agent '{agent_id}' auto-resumed after cooldown")

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

                print(f"[RATE LIMITER] Agent '{agent_id}' resumed")

    def get_status(self) -> dict:
        """Get current rate limiting status for UI.

        Returns:
            Dict with current status information
        """
        with self._lock:
            config = self._load_config()
            rolling_config = self._get_rolling_window_config()
            throttle_config = self._get_throttle_config()
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
                "throttle": {
                    "enabled": throttle_config.get("enabled", False),
                    "calls_per_minute": throttle_config.get("calls_per_minute", 10)
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
        """Get rate limiting stats for a specific agent.

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

        # Clean per-agent history
        for agent_id in list(self._agent_call_history.keys()):
            history = self._agent_call_history[agent_id]
            while history and history[0] < cutoff:
                history.popleft()

            # Remove empty histories
            if not history:
                del self._agent_call_history[agent_id]

    def _log_event(self, event_type: str, details: dict):
        """Log a rate limiting event."""
        self._logger.info({
            "event": event_type,
            **details
        })

    def invalidate_config(self):
        """Invalidate cached config. Call when settings change."""
        with self._lock:
            self._config_cache = None
            self._config_mtime = 0


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    with _rate_limiter_lock:
        if _rate_limiter is None:
            _rate_limiter = RateLimiter()
        return _rate_limiter
