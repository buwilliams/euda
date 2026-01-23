"""
Metacognition Module - Second-order thinking (self-awareness and self-regulation).

This module provides:
- Self-regulation (via regulation/): Token awareness, progress tracking, config, incidents
- Self-improvement (via consolidation/): Memory and identity consolidation (formerly Reflection)

The main Metacognition class orchestrates these capabilities for each agent.
"""

from .metacognition import Metacognition
from .regulation import (
    TokenAwareness,
    AgentState,
    AgentPausedError,
    get_token_awareness,
    get_calls_by_job,
    get_job_call_count,
    get_costs_by_agent,
    get_cost_summary,
    get_resource_tracker,
    MetacognitionConfig,
    ProgressTracker,
    count_tokens,
    estimate_request_tokens,
    IncidentTracker,
    Incident,
    IncidentType,
    IncidentSeverity,
    get_incident_tracker,
)
from .consolidation import Consolidation

__all__ = [
    # Main class
    "Metacognition",
    # Regulation
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
    # Consolidation (formerly Reflection)
    "Consolidation",
]
