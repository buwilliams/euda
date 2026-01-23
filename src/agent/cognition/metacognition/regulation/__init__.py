"""
Regulation Module - Self-regulation capabilities for agents.

Provides:
- Token awareness: Track tokens PRE-call, enforce per-agent budgets
- Progress awareness: Detect stuck/thrashing patterns
- Incident tracking: Log threshold breaches

This is the self-regulation aspect of metacognition.
"""

from .tokens import (
    TokenAwareness,
    AgentState,
    AgentPausedError,
    get_token_awareness,
    get_calls_by_job,
    get_job_call_count,
    get_costs_by_agent,
    get_cost_summary,
    get_resource_tracker,
)
from .config import MetacognitionConfig
from .progress import ProgressTracker
from .tokenizer import count_tokens, estimate_request_tokens
from .incidents import (
    IncidentTracker,
    Incident,
    IncidentType,
    IncidentSeverity,
    get_incident_tracker,
)

__all__ = [
    "TokenAwareness",
    "AgentState",
    "AgentPausedError",
    "get_token_awareness",
    "get_calls_by_job",
    "get_job_call_count",
    "get_costs_by_agent",
    "get_cost_summary",
    "get_resource_tracker",
    "MetacognitionConfig",
    "ProgressTracker",
    "count_tokens",
    "estimate_request_tokens",
    "IncidentTracker",
    "Incident",
    "IncidentType",
    "IncidentSeverity",
    "get_incident_tracker",
]
