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
