"""
Metacognition Module - Self-awareness and self-regulation for agents.

Metacognition answers "how do I regulate myself?" and provides:
- Velocity awareness: Track call rate, pause if too fast
- Resource awareness: Track costs, enforce budgets
- Action awareness: Monitor tool calls per iteration
- Progress awareness: Detect stuck/thrashing patterns
- Strategic planning: Think before acting

Every agent has metacognition - it's inherent, not optional.
"""

from .metacognition import Metacognition
from .velocity import (
    VelocityTracker,
    AgentPausedError,
    RateLimitExceeded,
    get_velocity_tracker,
)
from .resources import (
    ResourceTracker,
    BudgetExceeded,
    get_resource_tracker,
    record_usage,
    check_budget,
    get_cost_summary,
    get_costs_by_agent,
    get_calls_by_job,
    get_job_call_count,
)
from .config import MetacognitionConfig
from .progress import ProgressTracker
from .planning import Planner

__all__ = [
    "Metacognition",
    "MetacognitionConfig",
    "ProgressTracker",
    "Planner",
    # Velocity (rate limiting)
    "VelocityTracker",
    "AgentPausedError",
    "RateLimitExceeded",
    "get_velocity_tracker",
    # Resources (cost tracking)
    "ResourceTracker",
    "BudgetExceeded",
    "get_resource_tracker",
    "record_usage",
    "check_budget",
    "get_cost_summary",
    "get_costs_by_agent",
    "get_calls_by_job",
    "get_job_call_count",
]
