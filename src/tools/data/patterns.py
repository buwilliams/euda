"""
Pattern Tools - Query discovered patterns for anticipation.

Patterns are discovered during consolidation and stored per-agent.
These tools allow agents to query patterns during conversations.
"""

from typing import Optional

from .. import tool
from ...agent.cognition.metacognition.consolidation.patterns import (
    load_patterns,
    format_patterns_for_prompt,
    get_high_confidence_patterns,
    get_pending_hypotheses,
    validate_hypothesis as _validate_hypothesis,
    save_patterns,
)


@tool(
    "list_patterns",
    "List discovered patterns for an agent. Use when: understanding behavior patterns for anticipation, or checking what patterns have been discovered.",
    tool_type="data"
)
def list_patterns(
    agent_id: str = "user",
    pattern_type: str = None,
    min_confidence: float = 0.5
) -> dict:
    """List discovered patterns for an agent.

    Args:
        agent_id: Agent ID (defaults to "user")
        pattern_type: Filter by type - "temporal", "correlation", "trajectory", "hypothesis", or None for all
        min_confidence: Minimum confidence threshold (0.0 to 1.0)

    Returns:
        Dictionary with patterns organized by type
    """
    store = load_patterns(agent_id)

    result = {
        "agent_id": agent_id,
        "last_updated": store.last_updated,
    }

    # Filter by confidence
    def filter_by_confidence(patterns):
        return [p for p in patterns if p.get("confidence", 0) >= min_confidence]

    if pattern_type is None or pattern_type == "temporal":
        result["temporal"] = filter_by_confidence(store.temporal)

    if pattern_type is None or pattern_type == "correlation":
        result["correlations"] = filter_by_confidence(store.correlations)

    if pattern_type is None or pattern_type == "trajectory":
        result["trajectories"] = filter_by_confidence(store.trajectories)

    if pattern_type is None or pattern_type == "hypothesis":
        # For hypotheses, return pending ones (status filter, not confidence)
        result["hypotheses"] = [h for h in store.hypotheses if h["status"] == "pending"]

    # Add counts
    result["counts"] = {
        "temporal": len(result.get("temporal", [])),
        "correlations": len(result.get("correlations", [])),
        "trajectories": len(result.get("trajectories", [])),
        "hypotheses": len(result.get("hypotheses", []))
    }

    return result


@tool(
    "get_pattern_context",
    "Get formatted pattern summary for anticipation. Use when: preparing personalized responses or understanding user rhythms.",
    tool_type="data"
)
def get_pattern_context(
    agent_id: str = "user",
    min_confidence: float = 0.7
) -> str:
    """Get formatted pattern context for prompts.

    Returns a human-readable summary of high-confidence patterns
    suitable for inclusion in conversation context.

    Args:
        agent_id: Agent ID (defaults to "user")
        min_confidence: Minimum confidence threshold

    Returns:
        Formatted markdown string with pattern summary, or empty string if none
    """
    store = load_patterns(agent_id)
    formatted = format_patterns_for_prompt(store, min_confidence)

    if not formatted:
        return "No high-confidence patterns discovered yet."

    return formatted


@tool(
    "validate_pattern_hypothesis",
    "Record evidence for a pattern hypothesis. Use when: you observe something that supports a pending hypothesis.",
    tool_type="data"
)
def validate_pattern_hypothesis(
    hypothesis_id: str,
    evidence: str,
    agent_id: str = "user"
) -> dict:
    """Record evidence for a hypothesis.

    When enough evidence is collected, the hypothesis graduates to a pattern.

    Args:
        hypothesis_id: The hypothesis ID (e.g., "hyp-abc12345")
        evidence: Description of the evidence observed
        agent_id: Agent ID (defaults to "user")

    Returns:
        Status of the hypothesis after validation
    """
    store = load_patterns(agent_id)

    # Find the hypothesis
    hypothesis = None
    for h in store.hypotheses:
        if h["id"] == hypothesis_id:
            hypothesis = h
            break

    if not hypothesis:
        return {"error": f"Hypothesis not found: {hypothesis_id}"}

    if hypothesis["status"] != "pending":
        return {
            "error": f"Hypothesis is not pending (status: {hypothesis['status']})",
            "hypothesis_id": hypothesis_id
        }

    # Validate
    graduated = _validate_hypothesis(hypothesis, evidence)

    # Save updated store
    save_patterns(agent_id, store)

    return {
        "hypothesis_id": hypothesis_id,
        "evidence_added": evidence,
        "evidence_count": hypothesis["evidence_collected"],
        "evidence_required": hypothesis["evidence_required"],
        "status": hypothesis["status"],
        "graduated": graduated
    }
