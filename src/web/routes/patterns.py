"""
Patterns API Routes - Expose discovered patterns via REST API.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ...reflection.patterns import (
    load_patterns,
    save_patterns,
    format_patterns_for_prompt,
    get_high_confidence_patterns,
    validate_hypothesis as _validate_hypothesis,
)


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ValidateHypothesisRequest(BaseModel):
    """Request to validate a hypothesis with evidence."""
    evidence: str


class PatternResponse(BaseModel):
    """Response containing patterns for an agent."""
    agent_id: str
    temporal: List[Dict[str, Any]]
    correlations: List[Dict[str, Any]]
    trajectories: List[Dict[str, Any]]
    hypotheses: List[Dict[str, Any]]
    last_updated: str


# =============================================================================
# Pattern Endpoints
# =============================================================================

@router.get("/{agent_id}/patterns")
def api_get_patterns(
    agent_id: str,
    min_confidence: float = 0.0,
    pattern_type: Optional[str] = None
):
    """Get all patterns for an agent.

    Args:
        agent_id: Agent ID (e.g., "user", "chat")
        min_confidence: Minimum confidence threshold (0.0 to 1.0)
        pattern_type: Filter by type - "temporal", "correlation", "trajectory", "hypothesis"
    """
    store = load_patterns(agent_id)

    def filter_by_confidence(patterns):
        return [p for p in patterns if p.get("confidence", 0) >= min_confidence]

    result = {
        "agent_id": agent_id,
        "last_updated": store.last_updated,
    }

    if pattern_type is None or pattern_type == "temporal":
        result["temporal"] = filter_by_confidence(store.temporal)

    if pattern_type is None or pattern_type == "correlation":
        result["correlations"] = filter_by_confidence(store.correlations)

    if pattern_type is None or pattern_type == "trajectory":
        result["trajectories"] = filter_by_confidence(store.trajectories)

    if pattern_type is None or pattern_type == "hypothesis":
        result["hypotheses"] = store.hypotheses

    # Add counts
    result["counts"] = {
        "temporal": len(result.get("temporal", [])),
        "correlations": len(result.get("correlations", [])),
        "trajectories": len(result.get("trajectories", [])),
        "hypotheses": len(result.get("hypotheses", []))
    }

    return result


@router.get("/{agent_id}/patterns/temporal")
def api_get_temporal_patterns(agent_id: str, min_confidence: float = 0.0):
    """Get temporal patterns for an agent."""
    store = load_patterns(agent_id)
    patterns = [p for p in store.temporal if p.get("confidence", 0) >= min_confidence]
    return {
        "agent_id": agent_id,
        "temporal": patterns,
        "count": len(patterns)
    }


@router.get("/{agent_id}/patterns/correlations")
def api_get_correlations(agent_id: str, min_confidence: float = 0.0):
    """Get correlations for an agent."""
    store = load_patterns(agent_id)
    correlations = [c for c in store.correlations if c.get("confidence", 0) >= min_confidence]
    return {
        "agent_id": agent_id,
        "correlations": correlations,
        "count": len(correlations)
    }


@router.get("/{agent_id}/patterns/trajectories")
def api_get_trajectories(agent_id: str, min_confidence: float = 0.0):
    """Get trajectories for an agent."""
    store = load_patterns(agent_id)
    trajectories = [t for t in store.trajectories if t.get("confidence", 0) >= min_confidence]
    return {
        "agent_id": agent_id,
        "trajectories": trajectories,
        "count": len(trajectories)
    }


@router.get("/{agent_id}/patterns/hypotheses")
def api_get_hypotheses(agent_id: str, status: Optional[str] = None):
    """Get hypotheses for an agent.

    Args:
        agent_id: Agent ID
        status: Filter by status - "pending", "validated", "rejected", "expired"
    """
    store = load_patterns(agent_id)
    hypotheses = store.hypotheses

    if status:
        hypotheses = [h for h in hypotheses if h.get("status") == status]

    return {
        "agent_id": agent_id,
        "hypotheses": hypotheses,
        "count": len(hypotheses)
    }


@router.post("/{agent_id}/patterns/hypotheses/{hypothesis_id}/validate")
def api_validate_hypothesis(
    agent_id: str,
    hypothesis_id: str,
    request: ValidateHypothesisRequest
):
    """Record evidence for a hypothesis.

    When enough evidence is collected, the hypothesis graduates to a pattern.
    """
    store = load_patterns(agent_id)

    # Find the hypothesis
    hypothesis = None
    for h in store.hypotheses:
        if h["id"] == hypothesis_id:
            hypothesis = h
            break

    if not hypothesis:
        raise HTTPException(status_code=404, detail=f"Hypothesis not found: {hypothesis_id}")

    if hypothesis["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Hypothesis is not pending (status: {hypothesis['status']})"
        )

    # Validate
    graduated = _validate_hypothesis(hypothesis, request.evidence)

    # Save updated store
    save_patterns(agent_id, store)

    return {
        "hypothesis_id": hypothesis_id,
        "evidence_added": request.evidence,
        "evidence_count": hypothesis["evidence_collected"],
        "evidence_required": hypothesis["evidence_required"],
        "status": hypothesis["status"],
        "graduated": graduated
    }


@router.delete("/{agent_id}/patterns/{pattern_id}")
def api_delete_pattern(agent_id: str, pattern_id: str):
    """Remove a pattern by ID.

    Works for any pattern type (temporal, correlation, trajectory, hypothesis).
    """
    store = load_patterns(agent_id)
    deleted = False
    pattern_type = None

    # Check each pattern type
    for attr, ptype in [
        ("temporal", "temporal"),
        ("correlations", "correlation"),
        ("trajectories", "trajectory"),
        ("hypotheses", "hypothesis")
    ]:
        patterns = getattr(store, attr)
        original_count = len(patterns)
        filtered = [p for p in patterns if p.get("id") != pattern_id]
        if len(filtered) < original_count:
            setattr(store, attr, filtered)
            deleted = True
            pattern_type = ptype
            break

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

    save_patterns(agent_id, store)

    return {
        "deleted": pattern_id,
        "type": pattern_type,
        "agent_id": agent_id
    }


@router.get("/{agent_id}/patterns/context")
def api_get_pattern_context(agent_id: str, min_confidence: float = 0.7):
    """Get formatted pattern context for prompts.

    Returns a human-readable summary of high-confidence patterns
    suitable for inclusion in conversation context.
    """
    store = load_patterns(agent_id)
    context = format_patterns_for_prompt(store, min_confidence)

    return {
        "agent_id": agent_id,
        "min_confidence": min_confidence,
        "context": context if context else "No high-confidence patterns discovered yet."
    }


@router.get("/{agent_id}/patterns/high-confidence")
def api_get_high_confidence_patterns(agent_id: str, min_confidence: float = 0.7):
    """Get only high-confidence patterns for an agent."""
    store = load_patterns(agent_id)
    high_conf = get_high_confidence_patterns(store, min_confidence)

    return {
        "agent_id": agent_id,
        "min_confidence": min_confidence,
        **high_conf,
        "counts": {
            "temporal": len(high_conf["temporal"]),
            "correlations": len(high_conf["correlations"]),
            "trajectories": len(high_conf["trajectories"])
        }
    }
