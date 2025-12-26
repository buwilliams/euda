"""
Values tools for the Self Agent (The Keeper).

Values are derived from epistemic axioms - what you care about.

Tools for reading summaries and managing values at different temporal scopes:
- Current: Rolling year, what matters now
- Phase: Life phase values, detected through transitions
- Lifetime: Enduring values that persist across phases
"""

from datetime import datetime
from pathlib import Path

# Base paths - Self agent uses shared log and self data
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
LOG_DIR = SHARED_DIR / "lifelog"
SELF_DIR = DATA_DIR / "self"
VALUES_DIR = SELF_DIR / "values"

# Backwards compatibility
IDENTITY_DIR = SELF_DIR

# Ensure values directory exists
VALUES_DIR.mkdir(parents=True, exist_ok=True)


def get_all_summaries() -> str:
    """
    Read all yearly summaries.

    Returns:
        All summaries concatenated with year headers
    """
    if not LOG_DIR.exists():
        return "No log directory found"

    summaries = []
    for year_dir in sorted(LOG_DIR.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        summary_file = year_dir / "_summary.md"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                content = f.read()
            summaries.append(f"# {year_dir.name}\n\n{content}")

    if not summaries:
        return "No yearly summaries found. Run the Summary Agent first."

    return "\n\n---\n\n".join(summaries)


def get_summary(year: int) -> str:
    """
    Read the summary for a specific year.

    Args:
        year: The year to read summary for

    Returns:
        Summary content or message if not found
    """
    summary_file = LOG_DIR / str(year) / "_summary.md"

    if not summary_file.exists():
        return f"No summary found for {year}"

    with open(summary_file, 'r') as f:
        return f.read()


def get_current_values() -> str:
    """
    Read the current (rolling year) values.

    Returns:
        Current values or message if not found
    """
    values_file = VALUES_DIR / "current.values.md"

    if not values_file.exists():
        return "No current values defined yet."

    with open(values_file, 'r') as f:
        return f.read()


def get_phase_values() -> str:
    """
    Read the life phase values.

    Returns:
        Phase values or message if not found
    """
    values_file = VALUES_DIR / "phase.values.md"

    if not values_file.exists():
        return "No phase values defined yet."

    with open(values_file, 'r') as f:
        return f.read()


def get_lifetime_values() -> str:
    """
    Read the lifetime values.

    Returns:
        Lifetime values or message if not found
    """
    values_file = VALUES_DIR / "lifetime.values.md"

    if not values_file.exists():
        return "No lifetime values defined yet."

    with open(values_file, 'r') as f:
        return f.read()


def get_all_values() -> str:
    """
    Read all values (current, phase, lifetime).

    Returns:
        All values concatenated with headers
    """
    sections = []

    current = get_current_values()
    if not current.startswith("No current"):
        sections.append(f"## Current Values (Rolling Year)\n\n{current}")

    phase = get_phase_values()
    if not phase.startswith("No phase"):
        sections.append(f"## Life Phase Values\n\n{phase}")

    lifetime = get_lifetime_values()
    if not lifetime.startswith("No lifetime"):
        sections.append(f"## Lifetime Values\n\n{lifetime}")

    if not sections:
        return "No values defined yet. Analyze summaries to derive values."

    return "\n\n---\n\n".join(sections)


def write_current_values(content: str) -> str:
    """
    Write or update current (rolling year) values.

    Args:
        content: The values content in markdown format

    Returns:
        Confirmation message
    """
    values_file = VALUES_DIR / "current.values.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# Current Values

*Rolling year focus - what matters right now*

Updated: {timestamp}

{content}
"""

    with open(values_file, 'w') as f:
        f.write(full_content)

    return "Current values updated"


def write_phase_values(content: str, phase_name: str = "") -> str:
    """
    Write or update life phase values.

    Args:
        content: The values content in markdown format
        phase_name: Optional name for the current phase

    Returns:
        Confirmation message
    """
    values_file = VALUES_DIR / "phase.values.md"
    timestamp = datetime.now().isoformat()

    phase_header = f" - {phase_name}" if phase_name else ""

    full_content = f"""# Life Phase Values{phase_header}

*Values characteristic of this life phase*

Updated: {timestamp}

{content}
"""

    with open(values_file, 'w') as f:
        f.write(full_content)

    return f"Phase values updated{phase_header}"


def write_lifetime_values(content: str) -> str:
    """
    Write or update lifetime values.

    Args:
        content: The values content in markdown format

    Returns:
        Confirmation message
    """
    values_file = VALUES_DIR / "lifetime.values.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# Lifetime Values

*Enduring values that persist across phases*

Updated: {timestamp}

{content}
"""

    with open(values_file, 'w') as f:
        f.write(full_content)

    return "Lifetime values updated"


def note_value_tension(stated: str, revealed: str, reflection: str) -> str:
    """
    Record a tension between stated and revealed values.

    Args:
        stated: What the user says they value
        revealed: What behavior patterns suggest
        reflection: Thoughts on this tension

    Returns:
        Confirmation message
    """
    tensions_file = VALUES_DIR / "tensions.md"
    timestamp = datetime.now().isoformat()

    entry = f"""
---

## Tension noted: {timestamp}

**Stated**: {stated}

**Revealed**: {revealed}

**Reflection**: {reflection}

---
"""

    # Append to existing or create new
    if tensions_file.exists():
        with open(tensions_file, 'a') as f:
            f.write(entry)
    else:
        header = "# Value Tensions\n\n*Gaps between stated and revealed values - not hypocrisy, but growth opportunities*\n"
        with open(tensions_file, 'w') as f:
            f.write(header + entry)

    return "Value tension noted for reflection"


def get_value_tensions() -> str:
    """
    Read recorded value tensions.

    Returns:
        Tensions content or message if none
    """
    tensions_file = VALUES_DIR / "tensions.md"

    if not tensions_file.exists():
        return "No value tensions recorded yet."

    with open(tensions_file, 'r') as f:
        return f.read()


# Tool definitions for the LLM
VALUES_TOOLS = [
    {
        "name": "get_all_summaries",
        "description": "Read all yearly summaries. Use this to analyze patterns across years before deriving values.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_summary",
        "description": "Read the summary for a specific year.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year to read summary for"
                }
            },
            "required": ["year"]
        }
    },
    {
        "name": "get_all_values",
        "description": "Read all currently defined values (current, phase, and lifetime).",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_current_values",
        "description": "Read the current (rolling year) values - what matters right now.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_phase_values",
        "description": "Read the life phase values - values characteristic of this phase of life.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_lifetime_values",
        "description": "Read the lifetime values - enduring values that persist across phases.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_current_values",
        "description": "Write or update current (rolling year) values. These reflect what matters right now.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The values in plain language markdown format"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "write_phase_values",
        "description": "Write or update life phase values. Include phase_name if a phase has been identified.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The values in plain language markdown format"
                },
                "phase_name": {
                    "type": "string",
                    "description": "Optional name for the current life phase (e.g., 'Early Career', 'New Parent')"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "write_lifetime_values",
        "description": "Write or update lifetime values. These are enduring values that persist across all phases.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The values in plain language markdown format"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "note_value_tension",
        "description": "Record a tension between stated and revealed values. Not to expose hypocrisy, but to understand growth edges.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stated": {
                    "type": "string",
                    "description": "What the user says they value"
                },
                "revealed": {
                    "type": "string",
                    "description": "What behavior patterns suggest they value"
                },
                "reflection": {
                    "type": "string",
                    "description": "Thoughts on this tension and what it might mean"
                }
            },
            "required": ["stated", "revealed", "reflection"]
        }
    },
    {
        "name": "get_value_tensions",
        "description": "Read recorded value tensions - gaps between stated and revealed values.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handlers mapping
VALUES_HANDLERS = {
    "get_all_summaries": get_all_summaries,
    "get_summary": get_summary,
    "get_all_values": get_all_values,
    "get_current_values": get_current_values,
    "get_phase_values": get_phase_values,
    "get_lifetime_values": get_lifetime_values,
    "write_current_values": write_current_values,
    "write_phase_values": write_phase_values,
    "write_lifetime_values": write_lifetime_values,
    "note_value_tension": note_value_tension,
    "get_value_tensions": get_value_tensions,
}


# Test
if __name__ == "__main__":
    print(get_all_summaries()[:500])
    print()
    print(get_all_values())
