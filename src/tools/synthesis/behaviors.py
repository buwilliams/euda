"""
Behaviors tools for the Synthesis Agent (The Keeper).

Behaviors are DERIVED from patterns - how you actually act (revealed preferences).
These patterns are extracted from life log summaries and daily entries.
"""

from datetime import datetime
from pathlib import Path

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
BEHAVIORS_DIR = SYNTHESIS_DIR / "behaviors"

# Ensure directory exists
BEHAVIORS_DIR.mkdir(parents=True, exist_ok=True)


def get_behaviors() -> str:
    """
    Read the current behavioral patterns.

    Returns:
        Behavioral patterns content or message if not found
    """
    patterns_file = BEHAVIORS_DIR / "patterns.md"

    if not patterns_file.exists():
        return "No behavioral patterns derived yet."

    with open(patterns_file, 'r') as f:
        return f.read()


def write_behaviors(content: str) -> str:
    """
    Write or update behavioral patterns.

    Args:
        content: The patterns content in markdown format

    Returns:
        Confirmation message
    """
    patterns_file = BEHAVIORS_DIR / "patterns.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# Behavioral Patterns

*How you actually act - revealed preferences*

Updated: {timestamp}

{content}

---

*Derived from: summaries, log patterns*
"""

    with open(patterns_file, 'w') as f:
        f.write(full_content)

    return "Behavioral patterns updated"


def note_behavior_pattern(pattern: str, evidence: str) -> str:
    """
    Append a newly observed behavioral pattern.

    Args:
        pattern: Description of the pattern observed
        evidence: Evidence from logs/summaries supporting this pattern

    Returns:
        Confirmation message
    """
    patterns_file = BEHAVIORS_DIR / "patterns.md"
    timestamp = datetime.now().isoformat()

    entry = f"""
---

## Pattern noted: {timestamp}

**Pattern**: {pattern}

**Evidence**: {evidence}

---
"""

    # Append to existing or create new
    if patterns_file.exists():
        with open(patterns_file, 'a') as f:
            f.write(entry)
    else:
        header = """# Behavioral Patterns

*How you actually act - revealed preferences*

Updated: (see entries below)

"""
        with open(patterns_file, 'w') as f:
            f.write(header + entry)

    return "Behavioral pattern noted"


# Tool definitions for the LLM
BEHAVIOR_TOOLS = [
    {
        "name": "get_behaviors",
        "description": "Read the current behavioral patterns - how the user actually acts based on life log evidence.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_behaviors",
        "description": "Write or update the full behavioral patterns document. Use when deriving patterns from summaries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The behavioral patterns in plain language markdown format"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "note_behavior_pattern",
        "description": "Record a newly observed behavioral pattern with supporting evidence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Description of the behavioral pattern observed"
                },
                "evidence": {
                    "type": "string",
                    "description": "Evidence from logs or summaries that supports this pattern"
                }
            },
            "required": ["pattern", "evidence"]
        }
    }
]

# Tool handlers mapping
BEHAVIOR_HANDLERS = {
    "get_behaviors": get_behaviors,
    "write_behaviors": write_behaviors,
    "note_behavior_pattern": note_behavior_pattern,
}


# Test
if __name__ == "__main__":
    print(get_behaviors())
