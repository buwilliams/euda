"""
Pattern Storage and Management

Persistent storage for discovered patterns across consolidation cycles.
Patterns accumulate and strengthen over time through validation.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


# =============================================================================
# Configuration
# =============================================================================

def _load_patterns_config() -> dict:
    """Load patterns configuration from system config."""
    config_path = DATA_DIR / "system" / "config.json"
    defaults = {
        "enabled": True,
        "discovery_passes": ["temporal", "correlation", "trajectory"],
        "min_evidence_for_pattern": 3,
        "hypothesis_expiry_days": 30,
        "confidence_decay_rate": 0.1,
        "confidence_boost_on_validation": 0.15
    }

    if not config_path.exists():
        return defaults

    try:
        with open(config_path) as f:
            config = json.load(f)
        patterns_config = config.get("metacognition", {}).get("patterns", {})
        return {**defaults, **patterns_config}
    except (json.JSONDecodeError, KeyError):
        return defaults


# =============================================================================
# Schema Dataclasses
# =============================================================================

@dataclass
class TemporalPattern:
    """A time-based pattern (daily, weekly, seasonal)."""
    id: str
    description: str
    granularity: str  # "daily", "weekly", "seasonal"
    time_window: dict  # {"start": "08:00", "end": "09:00"} or {"day": "monday"}
    confidence: float
    evidence_count: int
    first_observed: str  # YYYY-MM-DD
    last_observed: str  # YYYY-MM-DD

    @classmethod
    def create(cls, description: str, granularity: str, time_window: dict) -> "TemporalPattern":
        today = datetime.now().strftime("%Y-%m-%d")
        return cls(
            id=f"tmp-{uuid.uuid4().hex[:8]}",
            description=description,
            granularity=granularity,
            time_window=time_window,
            confidence=0.5,  # Start neutral
            evidence_count=1,
            first_observed=today,
            last_observed=today
        )


@dataclass
class Correlation:
    """A correlation between two types of items."""
    id: str
    type: str  # "co_occurrence", "causal", "inverse"
    items: list  # [{"type": "concern", "pattern": "..."}, {"type": "behavior", "pattern": "..."}]
    lag_days: int  # 0 = same time, positive = second item follows first
    confidence: float
    evidence_count: int
    description: str
    first_observed: str
    last_observed: str

    @classmethod
    def create(cls, correlation_type: str, items: list, description: str, lag_days: int = 0) -> "Correlation":
        today = datetime.now().strftime("%Y-%m-%d")
        return cls(
            id=f"cor-{uuid.uuid4().hex[:8]}",
            type=correlation_type,
            items=items,
            lag_days=lag_days,
            confidence=0.5,
            evidence_count=1,
            description=description,
            first_observed=today,
            last_observed=today
        )


@dataclass
class TrajectoryStage:
    """A stage in a trajectory."""
    date: str
    state: str


@dataclass
class Trajectory:
    """An evolution of a goal, concern, or interest over time."""
    id: str
    type: str  # "goal_evolution", "concern_evolution", "interest_shift"
    subject: str  # What is evolving
    stages: list  # List of TrajectoryStage dicts
    direction: str  # "clarifying", "expanding", "resolving", "intensifying", "diminishing"
    confidence: float
    first_observed: str
    last_observed: str

    @classmethod
    def create(cls, trajectory_type: str, subject: str, initial_state: str, direction: str = "clarifying") -> "Trajectory":
        today = datetime.now().strftime("%Y-%m-%d")
        return cls(
            id=f"trj-{uuid.uuid4().hex[:8]}",
            type=trajectory_type,
            subject=subject,
            stages=[{"date": today, "state": initial_state}],
            direction=direction,
            confidence=0.5,
            first_observed=today,
            last_observed=today
        )


@dataclass
class Hypothesis:
    """An unvalidated pattern awaiting evidence."""
    id: str
    created_at: str  # ISO timestamp
    type: str  # "temporal", "correlation", "trajectory"
    hypothesis: str  # Human-readable description
    evidence_required: int
    evidence_collected: int
    evidence_details: list  # List of evidence observations
    status: str  # "pending", "validated", "rejected", "expired"
    expires_at: str  # ISO date

    @classmethod
    def create(cls, hypothesis_type: str, hypothesis: str, evidence_required: int = 3) -> "Hypothesis":
        config = _load_patterns_config()
        expiry_days = config.get("hypothesis_expiry_days", 30)
        now = datetime.now()
        expires = now + timedelta(days=expiry_days)

        return cls(
            id=f"hyp-{uuid.uuid4().hex[:8]}",
            created_at=now.isoformat(),
            type=hypothesis_type,
            hypothesis=hypothesis,
            evidence_required=evidence_required,
            evidence_collected=0,
            evidence_details=[],
            status="pending",
            expires_at=expires.strftime("%Y-%m-%d")
        )


# =============================================================================
# Pattern Storage Structure
# =============================================================================

@dataclass
class PatternStore:
    """Complete pattern storage for an agent."""
    version: int = 1
    last_updated: str = ""
    temporal: list = field(default_factory=list)  # List of TemporalPattern dicts
    correlations: list = field(default_factory=list)  # List of Correlation dicts
    trajectories: list = field(default_factory=list)  # List of Trajectory dicts
    hypotheses: list = field(default_factory=list)  # List of Hypothesis dicts

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()


# =============================================================================
# Path Helpers
# =============================================================================

def _get_patterns_dir(agent_id: str) -> Path:
    """Get the patterns directory for an agent."""
    return AGENTS_DIR / agent_id / "patterns"


def _ensure_patterns_dir(agent_id: str) -> Path:
    """Ensure patterns directory exists."""
    patterns_dir = _get_patterns_dir(agent_id)
    patterns_dir.mkdir(parents=True, exist_ok=True)
    return patterns_dir


# =============================================================================
# Load/Save Functions
# =============================================================================

def create_empty_patterns() -> PatternStore:
    """Create an empty pattern store."""
    return PatternStore()


def load_patterns(agent_id: str) -> PatternStore:
    """Load all patterns for an agent.

    Args:
        agent_id: The agent's ID

    Returns:
        PatternStore with all patterns, or empty store if none exist
    """
    patterns_dir = _get_patterns_dir(agent_id)

    if not patterns_dir.exists():
        return create_empty_patterns()

    store = PatternStore()

    # Load each pattern file
    for filename, attr in [
        ("temporal.json", "temporal"),
        ("correlations.json", "correlations"),
        ("trajectories.json", "trajectories"),
        ("hypotheses.json", "hypotheses")
    ]:
        filepath = patterns_dir / filename
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                setattr(store, attr, data.get("patterns", data.get("correlations", data.get("trajectories", data.get("hypotheses", [])))))
                if "last_updated" in data:
                    store.last_updated = data["last_updated"]
            except (json.JSONDecodeError, KeyError):
                continue

    return store


def save_patterns(agent_id: str, store: PatternStore) -> None:
    """Save all patterns for an agent.

    Args:
        agent_id: The agent's ID
        store: The PatternStore to save
    """
    patterns_dir = _ensure_patterns_dir(agent_id)
    store.last_updated = datetime.now().isoformat()

    # Save temporal patterns
    with open(patterns_dir / "temporal.json", "w") as f:
        json.dump({
            "version": store.version,
            "last_updated": store.last_updated,
            "patterns": store.temporal
        }, f, indent=2)

    # Save correlations
    with open(patterns_dir / "correlations.json", "w") as f:
        json.dump({
            "version": store.version,
            "last_updated": store.last_updated,
            "correlations": store.correlations
        }, f, indent=2)

    # Save trajectories
    with open(patterns_dir / "trajectories.json", "w") as f:
        json.dump({
            "version": store.version,
            "last_updated": store.last_updated,
            "trajectories": store.trajectories
        }, f, indent=2)

    # Save hypotheses
    with open(patterns_dir / "hypotheses.json", "w") as f:
        json.dump({
            "version": store.version,
            "last_updated": store.last_updated,
            "hypotheses": store.hypotheses
        }, f, indent=2)


# =============================================================================
# Pattern Management Functions
# =============================================================================

def add_temporal_pattern(store: PatternStore, pattern: TemporalPattern) -> None:
    """Add a temporal pattern to the store."""
    store.temporal.append(asdict(pattern))


def add_correlation(store: PatternStore, correlation: Correlation) -> None:
    """Add a correlation to the store."""
    store.correlations.append(asdict(correlation))


def add_trajectory(store: PatternStore, trajectory: Trajectory) -> None:
    """Add a trajectory to the store."""
    store.trajectories.append(asdict(trajectory))


def add_hypothesis(store: PatternStore, hypothesis: Hypothesis) -> None:
    """Add a hypothesis to the store."""
    store.hypotheses.append(asdict(hypothesis))


def find_similar_temporal(store: PatternStore, description: str, granularity: str) -> Optional[dict]:
    """Find a similar temporal pattern if one exists."""
    description_lower = description.lower()
    for pattern in store.temporal:
        if pattern["granularity"] == granularity:
            if description_lower in pattern["description"].lower() or pattern["description"].lower() in description_lower:
                return pattern
    return None


def find_similar_correlation(store: PatternStore, items: list) -> Optional[dict]:
    """Find a similar correlation if one exists."""
    for correlation in store.correlations:
        # Check if items overlap significantly
        existing_patterns = {item.get("pattern", "").lower() for item in correlation["items"]}
        new_patterns = {item.get("pattern", "").lower() for item in items}
        if existing_patterns & new_patterns:  # If there's overlap
            return correlation
    return None


def find_trajectory_by_subject(store: PatternStore, subject: str) -> Optional[dict]:
    """Find an existing trajectory for a subject."""
    subject_lower = subject.lower()
    for trajectory in store.trajectories:
        if subject_lower in trajectory["subject"].lower() or trajectory["subject"].lower() in subject_lower:
            return trajectory
    return None


# =============================================================================
# Confidence and Validation
# =============================================================================

def update_confidence(pattern: dict, validated: bool) -> None:
    """Update a pattern's confidence based on validation.

    Args:
        pattern: Pattern dict to update (modified in place)
        validated: Whether the pattern was validated
    """
    config = _load_patterns_config()

    if validated:
        boost = config.get("confidence_boost_on_validation", 0.15)
        pattern["confidence"] = min(1.0, pattern["confidence"] + boost)
        pattern["evidence_count"] = pattern.get("evidence_count", 0) + 1
        pattern["last_observed"] = datetime.now().strftime("%Y-%m-%d")
    else:
        decay = config.get("confidence_decay_rate", 0.1)
        pattern["confidence"] = max(0.0, pattern["confidence"] - decay)


def validate_hypothesis(hypothesis: dict, evidence: str) -> bool:
    """Record evidence for a hypothesis.

    Args:
        hypothesis: Hypothesis dict to update (modified in place)
        evidence: Description of the evidence

    Returns:
        True if hypothesis is now validated, False otherwise
    """
    if hypothesis["status"] != "pending":
        return hypothesis["status"] == "validated"

    hypothesis["evidence_collected"] += 1
    hypothesis["evidence_details"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "evidence": evidence
    })

    if hypothesis["evidence_collected"] >= hypothesis["evidence_required"]:
        hypothesis["status"] = "validated"
        return True

    return False


def cleanup_expired_hypotheses(store: PatternStore) -> list:
    """Remove expired hypotheses and return them.

    Args:
        store: PatternStore to clean up

    Returns:
        List of expired hypotheses that were removed
    """
    today = datetime.now().strftime("%Y-%m-%d")
    expired = []
    remaining = []

    for hyp in store.hypotheses:
        if hyp["status"] == "pending" and hyp["expires_at"] < today:
            hyp["status"] = "expired"
            expired.append(hyp)
        elif hyp["status"] not in ("expired", "rejected"):
            remaining.append(hyp)

    store.hypotheses = remaining
    return expired


def get_pending_hypotheses(store: PatternStore) -> list:
    """Get all pending hypotheses."""
    return [h for h in store.hypotheses if h["status"] == "pending"]


def apply_confidence_decay(store: PatternStore, validated_ids: set) -> int:
    """Apply confidence decay to patterns that weren't validated this cycle.

    Patterns that weren't re-observed during consolidation decay in confidence.
    This implements the "decay without validation" design principle.

    Args:
        store: PatternStore to update
        validated_ids: Set of pattern IDs that were validated this cycle

    Returns:
        Number of patterns that decayed
    """
    config = _load_patterns_config()
    decay_rate = config.get("confidence_decay_rate", 0.1)
    min_confidence_to_keep = 0.1  # Remove patterns below this threshold

    decayed_count = 0
    to_remove = []

    # Decay temporal patterns
    for pattern in store.temporal:
        if pattern["id"] not in validated_ids:
            pattern["confidence"] = max(0.0, pattern["confidence"] - decay_rate)
            decayed_count += 1
            if pattern["confidence"] < min_confidence_to_keep:
                to_remove.append(("temporal", pattern["id"]))

    # Decay correlations
    for pattern in store.correlations:
        if pattern["id"] not in validated_ids:
            pattern["confidence"] = max(0.0, pattern["confidence"] - decay_rate)
            decayed_count += 1
            if pattern["confidence"] < min_confidence_to_keep:
                to_remove.append(("correlation", pattern["id"]))

    # Decay trajectories
    for pattern in store.trajectories:
        if pattern["id"] not in validated_ids:
            pattern["confidence"] = max(0.0, pattern["confidence"] - decay_rate)
            decayed_count += 1
            if pattern["confidence"] < min_confidence_to_keep:
                to_remove.append(("trajectory", pattern["id"]))

    # Remove patterns that fell below threshold
    for ptype, pid in to_remove:
        if ptype == "temporal":
            store.temporal = [p for p in store.temporal if p["id"] != pid]
        elif ptype == "correlation":
            store.correlations = [p for p in store.correlations if p["id"] != pid]
        elif ptype == "trajectory":
            store.trajectories = [p for p in store.trajectories if p["id"] != pid]

    return decayed_count


def get_high_confidence_patterns(store: PatternStore, min_confidence: float = 0.7) -> dict:
    """Get all patterns above a confidence threshold.

    Args:
        store: PatternStore to search
        min_confidence: Minimum confidence threshold

    Returns:
        Dict with temporal, correlations, trajectories lists
    """
    return {
        "temporal": [p for p in store.temporal if p["confidence"] >= min_confidence],
        "correlations": [c for c in store.correlations if c["confidence"] >= min_confidence],
        "trajectories": [t for t in store.trajectories if t["confidence"] >= min_confidence]
    }


# =============================================================================
# Pattern Formatting for Prompts
# =============================================================================

def format_patterns_for_prompt(store: PatternStore, min_confidence: float = 0.6) -> str:
    """Format patterns for inclusion in consolidation prompts.

    Args:
        store: PatternStore to format
        min_confidence: Minimum confidence to include

    Returns:
        Markdown-formatted string of patterns
    """
    lines = ["## Discovered Patterns", ""]

    # Temporal patterns
    temporal = [p for p in store.temporal if p["confidence"] >= min_confidence]
    if temporal:
        lines.append("### Temporal Patterns")
        for p in temporal:
            lines.append(f"- **{p['granularity'].title()}**: {p['description']} (confidence: {p['confidence']:.0%})")
        lines.append("")

    # Correlations
    correlations = [c for c in store.correlations if c["confidence"] >= min_confidence]
    if correlations:
        lines.append("### Correlations")
        for c in correlations:
            lines.append(f"- {c['description']} (confidence: {c['confidence']:.0%})")
        lines.append("")

    # Trajectories
    trajectories = [t for t in store.trajectories if t["confidence"] >= min_confidence]
    if trajectories:
        lines.append("### Trajectories")
        for t in trajectories:
            direction_emoji = {
                "clarifying": "🎯",
                "expanding": "📈",
                "resolving": "✅",
                "intensifying": "⚡",
                "diminishing": "📉"
            }.get(t["direction"], "→")
            lines.append(f"- {direction_emoji} **{t['subject']}**: {t['direction']} ({len(t['stages'])} stages, confidence: {t['confidence']:.0%})")
        lines.append("")

    # Pending hypotheses
    pending = get_pending_hypotheses(store)
    if pending:
        lines.append("### Hypotheses Under Investigation")
        for h in pending:
            lines.append(f"- {h['hypothesis']} ({h['evidence_collected']}/{h['evidence_required']} evidence)")
        lines.append("")

    if len(lines) == 2:  # Only header
        return ""

    return "\n".join(lines)


# =============================================================================
# Hypothesis Generation
# =============================================================================

def generate_hypothesis_from_finding(finding_type: str, finding: str) -> Hypothesis:
    """Generate a hypothesis from an RLM finding.

    Args:
        finding_type: Type of pattern (temporal, correlation, trajectory)
        finding: Description of the potential pattern

    Returns:
        New Hypothesis object
    """
    config = _load_patterns_config()
    evidence_required = config.get("min_evidence_for_pattern", 3)

    return Hypothesis.create(
        hypothesis_type=finding_type,
        hypothesis=finding,
        evidence_required=evidence_required
    )
