"""
Profile observation signals for Euno.

Implements the signal-based contribution model from governance.md.
Agents emit observations; Synthesis consumes and integrates them.

Signal types:
- behavioral_pattern: Recurring action observed
- constraint_evidence: Identity constraint revealed
- failure_mode_trigger: Stress response observed
- value_expression: Value demonstrated in action
- change_signal: Possible identity shift
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SIGNALS_DIR = DATA_DIR / "shared" / "signals"
OBSERVATIONS_FILE = SIGNALS_DIR / "profile_observations.json"

# Ensure directory exists
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

# Valid signal types
SIGNAL_TYPES = [
    "behavioral_pattern",
    "constraint_evidence",
    "failure_mode_trigger",
    "value_expression",
    "change_signal",
]


def _load_observations() -> dict:
    """Load current observations from file."""
    if OBSERVATIONS_FILE.exists():
        try:
            with open(OBSERVATIONS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"observations": []}
    return {"observations": []}


def _save_observations(data: dict):
    """Save observations to file."""
    with open(OBSERVATIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def emit_profile_observation(
    agent: str,
    signal_type: str,
    observation: str,
    evidence: Optional[str] = None,
    confidence: str = "medium",
    suggested_section: Optional[str] = None,
    suggested_action: Optional[str] = None,
    suggested_pattern: Optional[str] = None
) -> str:
    """
    Emit a profile observation signal.

    Called by agents when they observe something relevant to the user's profile.
    Synthesis Agent will read and integrate these observations.

    Args:
        agent: Name of the emitting agent
        signal_type: One of: behavioral_pattern, constraint_evidence,
                     failure_mode_trigger, value_expression, change_signal
        observation: Description of what was observed
        evidence: Optional path to evidence (e.g., "lifelog/2025/2025-12-27.md")
        confidence: high, medium, or low
        suggested_section: Optional profile section to update
        suggested_action: Optional action (strengthen, weaken, add, remove)
        suggested_pattern: Optional pattern description

    Returns:
        Confirmation message with observation ID
    """
    if signal_type not in SIGNAL_TYPES:
        return f"Invalid signal type: {signal_type}. Must be one of: {SIGNAL_TYPES}"

    if confidence not in ["high", "medium", "low"]:
        return f"Invalid confidence: {confidence}. Must be: high, medium, or low"

    # Generate observation ID
    timestamp = datetime.now()
    obs_id = f"obs_{timestamp.strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"

    # Build observation
    obs = {
        "id": obs_id,
        "agent": agent,
        "timestamp": timestamp.isoformat(),
        "type": signal_type,
        "observation": observation,
        "confidence": confidence,
    }

    if evidence:
        obs["evidence"] = evidence

    if suggested_section or suggested_action or suggested_pattern:
        obs["suggested_update"] = {}
        if suggested_section:
            obs["suggested_update"]["section"] = suggested_section
        if suggested_action:
            obs["suggested_update"]["action"] = suggested_action
        if suggested_pattern:
            obs["suggested_update"]["pattern"] = suggested_pattern

    # Add to observations
    data = _load_observations()
    data["observations"].append(obs)
    _save_observations(data)

    return f"Observation emitted: {obs_id}"


def get_pending_observations() -> str:
    """
    Get all pending profile observations.

    Called by Synthesis Agent to read accumulated observations.

    Returns:
        JSON string of all pending observations
    """
    data = _load_observations()

    if not data["observations"]:
        return "No pending profile observations."

    return json.dumps(data, indent=2)


def consume_observations() -> list[dict]:
    """
    Consume and clear all pending observations.

    Called by Synthesis Agent after integrating observations.

    Returns:
        List of consumed observations
    """
    data = _load_observations()
    observations = data["observations"]

    # Clear the file
    _save_observations({"observations": []})

    return observations


def count_pending_observations() -> int:
    """
    Count pending observations without consuming them.

    Returns:
        Number of pending observations
    """
    data = _load_observations()
    return len(data["observations"])


# Tool definitions for agents that can emit observations
PROFILE_SIGNAL_TOOLS = [
    {
        "name": "emit_profile_observation",
        "description": """Emit an observation about the user's behavior or identity for the Synthesis Agent to consider.
Use this when you observe something that might be relevant to the user's profile:
- Behavioral patterns (recurring actions)
- Identity constraints (things they won't compromise on)
- Failure modes (stress responses)
- Value expressions (values demonstrated in action)
- Change signals (possible identity shifts)

Synthesis has final authority on whether to integrate observations.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Your agent name"
                },
                "signal_type": {
                    "type": "string",
                    "enum": SIGNAL_TYPES,
                    "description": "Type of observation"
                },
                "observation": {
                    "type": "string",
                    "description": "What you observed"
                },
                "evidence": {
                    "type": "string",
                    "description": "Path to evidence (optional)"
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level (default: medium)"
                },
                "suggested_section": {
                    "type": "string",
                    "description": "Profile section to update (optional)"
                },
                "suggested_action": {
                    "type": "string",
                    "enum": ["strengthen", "weaken", "add", "remove"],
                    "description": "Suggested action (optional)"
                },
                "suggested_pattern": {
                    "type": "string",
                    "description": "Pattern description (optional)"
                }
            },
            "required": ["agent", "signal_type", "observation"]
        }
    }
]

# Tool definitions for Synthesis Agent (consumer)
SYNTHESIS_SIGNAL_TOOLS = [
    {
        "name": "get_pending_observations",
        "description": "Get all pending profile observations from other agents.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "consume_observations",
        "description": "Consume and clear all pending observations after integrating them.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Handlers
PROFILE_SIGNAL_HANDLERS = {
    "emit_profile_observation": emit_profile_observation,
}

SYNTHESIS_SIGNAL_HANDLERS = {
    "get_pending_observations": get_pending_observations,
    "consume_observations": consume_observations,
}


if __name__ == "__main__":
    # Test
    print("Emitting test observation...")
    result = emit_profile_observation(
        agent="interaction",
        signal_type="behavioral_pattern",
        observation="User declined social invitation citing need for rest",
        evidence="lifelog/2025/2025-12-27.md",
        confidence="medium",
        suggested_section="Failure Modes",
        suggested_action="strengthen",
        suggested_pattern="Withdraws under social saturation"
    )
    print(result)

    print("\nPending observations:")
    print(get_pending_observations())

    print(f"\nCount: {count_pending_observations()}")
