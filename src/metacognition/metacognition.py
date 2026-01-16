"""
Metacognition - The agent's self-awareness and self-regulation system.

Metacognition answers "how do I regulate myself?" and is inherent to all agents.
It provides a unified interface for:
- Velocity awareness (rate limiting)
- Resource awareness (budget/cost tracking)
- Action awareness (tool call tracking)
- Progress awareness (stuck detection)
- Strategic planning

This is the Cognition subsystem of the agent ontology:
Agent = Identity + Cognition + Memory + Behavior

Where Cognition = Reasoning (prompts) + Metacognition (self-regulation)
"""

from typing import Optional, TYPE_CHECKING

from .config import MetacognitionConfig
from .velocity import get_velocity_tracker, VelocityTracker
from .resources import get_resource_tracker, ResourceTracker
from .planning import Planner
from ..logger import get_logger

if TYPE_CHECKING:
    from ..agent import Agent


class Metacognition:
    """The agent's self-awareness and self-regulation system.

    Every agent has metacognition - it's inherent, not optional.
    Just like every agent has a profile and memory.

    Metacognition provides:
    - Velocity awareness: Track call rate, pause if too fast
    - Resource awareness: Track costs, enforce budgets
    - Action awareness: Monitor tool calls per iteration (Phase 2)
    - Progress awareness: Detect stuck patterns (Phase 3)
    - Strategic planning: Plan approach before execution (Phase 5)
    """

    def __init__(self, agent: "Agent"):
        """Initialize metacognition for an agent.

        Args:
            agent: The agent this metacognition belongs to
        """
        self.agent = agent
        self.agent_id = agent.id

        # Config (merges system defaults with agent overrides)
        self.config = MetacognitionConfig(agent.id)

        # Global trackers (shared across all agents)
        self._velocity: VelocityTracker = get_velocity_tracker()
        self._resources: ResourceTracker = get_resource_tracker()

        # Per-agent tracking state (for action/progress awareness - Phase 2/3)
        self._tool_call_count: int = 0
        self._iteration_count: int = 0
        self._tool_history: list = []

        # Strategic planning (Phase 5)
        self.planner = Planner(agent)

        # Logger
        self._logger = get_logger(f"agents/{agent.id}/metacognition")

    # ============== Velocity Awareness ==============

    def acquire_velocity(self, job_id: Optional[str] = None) -> bool:
        """Acquire permission for an LLM call (velocity check).

        This should be called BEFORE making an LLM API call.

        Args:
            job_id: Optional job ID for tracking

        Returns:
            True if call can proceed

        Raises:
            AgentPausedError: If agent is paused due to runaway detection
            RateLimitExceeded: If rate limit exceeded
        """
        return self._velocity.acquire(self.agent_id, job_id)

    def record_velocity(self, job_id: Optional[str] = None):
        """Record a completed LLM call for velocity tracking.

        This should be called AFTER a successful LLM API call.

        Args:
            job_id: Optional job ID for tracking
        """
        self._velocity.record_call(self.agent_id, job_id)

    def is_paused(self) -> bool:
        """Check if this agent is paused due to runaway detection."""
        return self._velocity.is_agent_paused(self.agent_id)

    def get_pause_info(self) -> dict:
        """Get pause information for this agent."""
        return self._velocity.get_pause_info(self.agent_id)

    def resume(self):
        """Resume this agent if paused."""
        self._velocity.resume_agent(self.agent_id)

    def get_velocity_stats(self) -> dict:
        """Get velocity statistics for this agent."""
        return self._velocity.get_agent_stats(self.agent_id)

    # ============== Resource Awareness ==============

    def check_budget(self):
        """Check if budget is exceeded.

        Raises:
            BudgetExceeded: If budget limit reached
        """
        self._resources.check_budget()

    def get_resource_stats(self) -> dict:
        """Get resource (cost) statistics."""
        return self._resources.get_stats()

    def get_cost_summary(self) -> dict:
        """Get cost summary for session, today, 7 days, and month."""
        return self._resources.get_summary()

    # ============== Action Awareness (Phase 2) ==============

    def get_max_tool_calls_per_iteration(self) -> int:
        """Get the maximum tool calls allowed per iteration."""
        progress_config = self.config.get_progress_config()
        return progress_config.get("max_tool_calls_per_iteration", 50)

    def record_tool_call(self, tool_name: str, tool_input: dict):
        """Record a tool call for action/progress tracking.

        Args:
            tool_name: Name of the tool called
            tool_input: Input parameters to the tool
        """
        self._tool_call_count += 1
        self._tool_history.append({
            "tool": tool_name,
            "input": tool_input
        })

        # Keep history bounded
        if len(self._tool_history) > 200:
            self._tool_history = self._tool_history[-100:]

    def get_tool_call_count(self) -> int:
        """Get the current tool call count for this iteration."""
        return self._tool_call_count

    def check_tool_call_limit(self) -> bool:
        """Check if tool call limit has been reached.

        Returns:
            True if limit reached, False otherwise
        """
        max_calls = self.get_max_tool_calls_per_iteration()
        if self._tool_call_count >= max_calls:
            self.log("tool_limit_reached", {"count": self._tool_call_count, "limit": max_calls})
            return True
        return False

    def reset_iteration(self):
        """Reset per-iteration tracking state."""
        self._tool_call_count = 0
        self._iteration_count += 1

    def reset_work_cycle(self):
        """Reset tracking state for a new work cycle."""
        self._tool_call_count = 0
        self._iteration_count = 0
        self._tool_history = []

    # ============== Progress Awareness (Phase 3) ==============

    def get_max_repeated_tool_calls(self) -> int:
        """Get the maximum repeated tool calls before stuck detection."""
        progress_config = self.config.get_progress_config()
        return progress_config.get("max_repeated_tool_calls", 3)

    def check_stuck(self) -> Optional[str]:
        """Check if the agent appears stuck.

        Returns:
            Reason string if stuck, None if making progress
        """
        if len(self._tool_history) < 3:
            return None

        max_repeated = self.get_max_repeated_tool_calls()

        # Check for same tool called repeatedly with identical inputs
        recent = self._tool_history[-max_repeated:]
        if len(recent) >= max_repeated:
            first = recent[0]
            if all(t["tool"] == first["tool"] and t["input"] == first["input"] for t in recent):
                return f"Same tool '{first['tool']}' called {max_repeated} times with identical inputs"

        return None

    # ============== Planning (Phase 5) ==============

    def should_plan(self, job: dict) -> bool:
        """Check if planning is enabled for this job type.

        Args:
            job: The job dict to check

        Returns:
            True if planning should be done for this job
        """
        planning_config = self.config.get_planning_config()
        enabled_for = planning_config.get("enabled_for", [])

        job_name = job.get("name", "")
        job_tags = job.get("tags", [])

        # Check if job type matches enabled planning triggers
        if "exploration" in enabled_for:
            if "trigger:exploration" in job_tags or job_name.startswith("Trigger:exploration"):
                return True

        if "reflection" in enabled_for:
            if "trigger:reflection" in job_tags or job_name.startswith("Trigger:reflection"):
                return True

        return False

    # ============== Efficiency (Phase 4) ==============

    def should_defer_reflection(self) -> bool:
        """Check if reflection should be deferred until end of work cycle."""
        efficiency_config = self.config.get_efficiency_config()
        return efficiency_config.get("defer_reflection_in_work_cycles", True)

    # ============== Combined Status ==============

    def get_status(self) -> dict:
        """Get complete metacognition status for this agent.

        Returns:
            Dict with all metacognition state
        """
        return {
            "agent_id": self.agent_id,
            "velocity": self.get_velocity_stats(),
            "resources": self.get_resource_stats(),
            "action": {
                "tool_call_count": self._tool_call_count,
                "max_tool_calls": self.get_max_tool_calls_per_iteration(),
                "iteration_count": self._iteration_count
            },
            "progress": {
                "tool_history_length": len(self._tool_history),
                "is_stuck": self.check_stuck() is not None,
                "stuck_reason": self.check_stuck()
            },
            "paused": self.is_paused(),
            "pause_info": self.get_pause_info()
        }

    def get_progress_context(self) -> dict:
        """Get progress context for injecting into continue prompt (Phase 6).

        Returns:
            Dict with progress info for prompt injection
        """
        stuck_reason = self.check_stuck()
        return {
            "iteration": self._iteration_count,
            "tool_calls_this_cycle": self._tool_call_count,
            "max_tool_calls": self.get_max_tool_calls_per_iteration(),
            "approaching_limit": self._tool_call_count > (self.get_max_tool_calls_per_iteration() * 0.8),
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
        self._velocity.invalidate_config()
        self._resources.invalidate_config()
