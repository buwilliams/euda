"""
Agent Module - Generic agent implementation following the Agent Ontology.

Agent = Identity + Cognition + Memory + Behavior

Where:
- Identity: Purpose, values, voice (from identity.md)
- Cognition: Reasoning (prompts) + Metacognition (self-regulation, consolidation)
- Memory: Short-term (90 days) + Long-term (permanent archive)
- Behavior: Tools + Triggers + Modes (from config.json)
"""

from pathlib import Path
from .agent import Agent
from .interests import (
    Observation,
    get_observing_agents,
    get_agent_interests,
    matches_interests,
    check_content_for_observations,
    invalidate_interest_cache,
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"

__all__ = [
    "Agent",
    "DATA_DIR",
    "AGENTS_DIR",
    "Observation",
    "get_observing_agents",
    "get_agent_interests",
    "matches_interests",
    "check_content_for_observations",
    "invalidate_interest_cache",
]
