"""
Agent Guidance Tools - Read steering guidance from Evolution

Allows agents to check if there's guidance they should follow,
such as learning the user's name naturally or skipping certain features.
"""

import json
from pathlib import Path
from typing import Optional


# Path to guidance signal
SIGNALS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "shared" / "signals"


def get_guidance(agent_name: Optional[str] = None) -> dict:
    """
    Get guidance for an agent (or all guidance).

    Args:
        agent_name: Optional agent name to get specific guidance for

    Returns:
        Guidance dict or empty dict if no guidance exists.
    """
    guidance_file = SIGNALS_DIR / "agent_guidance.json"

    if not guidance_file.exists():
        return {}

    try:
        data = json.loads(guidance_file.read_text())
        all_guidance = data.get("guidance", {})

        if agent_name:
            return all_guidance.get(agent_name, {})
        return all_guidance
    except:
        return {}


def get_interaction_hints() -> str:
    """
    Get hints for the Interaction agent about what to learn naturally.

    Returns:
        Human-readable hints string.
    """
    guidance = get_guidance("interaction")

    if not guidance:
        return "No special guidance at this time."

    hints = []

    if guidance.get("learn_name_naturally"):
        hints.append("- The user's name is not yet known. If natural in conversation, ask what they'd like to be called.")

    if guidance.get("learn_location_naturally"):
        hints.append("- The user's location is not known. If relevant, ask where they're based.")

    if not hints:
        return "No special guidance at this time."

    return "Guidance from Evolution:\n" + "\n".join(hints)


def get_world_hints() -> str:
    """
    Get hints for the World agent about what to skip or prioritize.

    Returns:
        Human-readable hints string.
    """
    guidance = get_guidance("world")

    if not guidance:
        return "No special guidance at this time."

    hints = []

    if guidance.get("skip_location_opportunities"):
        hints.append("- User location is unknown. Skip location-based opportunities for now.")

    if not hints:
        return "No special guidance at this time."

    return "Guidance from Evolution:\n" + "\n".join(hints)


def should_skip_location_opportunities() -> bool:
    """Check if World agent should skip location-based opportunities."""
    guidance = get_guidance("world")
    return guidance.get("skip_location_opportunities", False)


def should_learn_name() -> bool:
    """Check if Interaction agent should try to learn user's name."""
    guidance = get_guidance("interaction")
    return guidance.get("learn_name_naturally", False)


# Tool definitions
GUIDANCE_TOOLS = [
    {
        "name": "get_guidance",
        "description": "Get steering guidance from Evolution agent. Returns hints about what to prioritize or skip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Optional agent name to get specific guidance for"
                }
            }
        }
    },
    {
        "name": "get_interaction_hints",
        "description": "Get hints for the Interaction agent about what to learn naturally in conversation.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_world_hints",
        "description": "Get hints for the World agent about what to skip or prioritize.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

GUIDANCE_HANDLERS = {
    "get_guidance": get_guidance,
    "get_interaction_hints": get_interaction_hints,
    "get_world_hints": get_world_hints,
}
