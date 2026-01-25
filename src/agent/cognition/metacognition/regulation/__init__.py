"""
Regulation Module - Self-regulation capabilities for agents.

Provides:
- Token awareness: Track tokens, enforce per-agent budgets
- Progress tracking: Detect stuck/spinning behavior
- Incident tracking: Log threshold breaches

This is the self-regulation aspect of metacognition.
"""

from .tokens import (
    TokenAwareness,
    AgentState,
    AgentPausedError,
    get_token_awareness,
    get_calls_by_topic,
    get_topic_call_count,
    get_costs_by_agent,
    get_cost_summary,
    get_resource_tracker,
)
from .config import MetacognitionConfig
from .tokenizer import count_tokens, estimate_request_tokens
from .incidents import (
    IncidentTracker,
    Incident,
    IncidentType,
    IncidentSeverity,
    get_incident_tracker,
)
from .progress import (
    ProgressTracker,
    SessionProgress,
    ProgressLimitExceeded,
    get_progress_tracker,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_RECURSION_DEPTH,
)

__all__ = [
    "TokenAwareness",
    "AgentState",
    "AgentPausedError",
    "get_token_awareness",
    "get_calls_by_topic",
    "get_topic_call_count",
    "get_costs_by_agent",
    "get_cost_summary",
    "get_resource_tracker",
    "MetacognitionConfig",
    "count_tokens",
    "estimate_request_tokens",
    "IncidentTracker",
    "Incident",
    "IncidentType",
    "IncidentSeverity",
    "get_incident_tracker",
    "ProgressTracker",
    "SessionProgress",
    "ProgressLimitExceeded",
    "get_progress_tracker",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_MAX_RECURSION_DEPTH",
]
