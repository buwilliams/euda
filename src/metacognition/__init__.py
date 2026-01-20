"""
Metacognition Module - Self-awareness and self-regulation for agents.

Metacognition answers "how do I regulate myself?" and provides:
- Token awareness: Track tokens PRE-call, enforce per-agent budgets
- Velocity awareness: Track call rate, pause if too fast (legacy)
- Resource awareness: Track costs, enforce budgets (legacy)
- Action awareness: Monitor tool calls per iteration
- Progress awareness: Detect stuck/thrashing patterns
- Strategic planning: Think before acting

Every agent has metacognition - it's inherent, not optional.
"""

from .metacognition import Metacognition
from .velocity import (
    VelocityTracker,
    AgentPausedError as VelocityAgentPausedError,
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

# New token awareness system
from .tokens import (
    TokenAwareness,
    AgentState,
    AgentPausedError,
    get_token_awareness,
)
from .tokenizer import count_tokens, estimate_request_tokens
from .incidents import (
    IncidentTracker,
    Incident,
    IncidentType,
    IncidentSeverity,
    get_incident_tracker,
)

__all__ = [
    "Metacognition",
    "MetacognitionConfig",
    "ProgressTracker",
    "Planner",
    # Token awareness (new unified system)
    "TokenAwareness",
    "AgentState",
    "AgentPausedError",
    "get_token_awareness",
    "count_tokens",
    "estimate_request_tokens",
    # Incidents
    "IncidentTracker",
    "Incident",
    "IncidentType",
    "IncidentSeverity",
    "get_incident_tracker",
    # Velocity (rate limiting) - legacy, kept for backward compatibility
    "VelocityTracker",
    "RateLimitExceeded",
    "get_velocity_tracker",
    # Resources (cost tracking) - legacy, kept for backward compatibility
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
