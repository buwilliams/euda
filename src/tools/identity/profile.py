"""
Profile tools for the Identity Agent (The Keeper).

The profile consolidates all identity facets into a single view for other agents.
It emphasizes VALUES at the core, with behaviors and context as supporting information.
"""

from datetime import datetime
from pathlib import Path

# Import from sibling modules
from .values import get_current_values, get_phase_values, get_lifetime_values
from .behaviors import get_behaviors
from .context import get_biographical, get_relationships

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
IDENTITY_DIR = DATA_DIR / "identity"
DERIVED_DIR = IDENTITY_DIR / "derived"

# Ensure directory exists
DERIVED_DIR.mkdir(parents=True, exist_ok=True)


def get_profile() -> str:
    """
    Read the consolidated identity profile.

    Returns:
        Profile content or message if not found
    """
    profile_file = DERIVED_DIR / "profile.md"

    if not profile_file.exists():
        return "No identity profile generated yet. Run generate_profile() to create one."

    with open(profile_file, 'r') as f:
        return f.read()


def generate_profile() -> str:
    """
    Generate a consolidated identity profile from all sources.

    The profile emphasizes values at the core, with behaviors and context
    as supporting information.

    Returns:
        Confirmation message with summary
    """
    profile_file = DERIVED_DIR / "profile.md"
    timestamp = datetime.now().isoformat()

    # Gather all identity data
    current_values = get_current_values()
    phase_values = get_phase_values()
    lifetime_values = get_lifetime_values()
    behaviors = get_behaviors()
    biographical = get_biographical()
    relationships = get_relationships()

    # Build the profile with values at the core
    sections = []

    # Core: Values
    sections.append("## Values (Core Identity)\n")
    sections.append("*What you believe and care about - the foundation of who you are*\n")

    if not current_values.startswith("No current"):
        # Extract just the content, not the full header
        sections.append("\n### Current Focus\n")
        sections.append(_extract_content(current_values))

    if not lifetime_values.startswith("No lifetime"):
        sections.append("\n### Enduring Beliefs\n")
        sections.append(_extract_content(lifetime_values))

    if not phase_values.startswith("No phase"):
        sections.append("\n### Life Phase Values\n")
        sections.append(_extract_content(phase_values))

    # Derived: Behaviors
    sections.append("\n---\n\n## Behavioral Patterns (Derived)\n")
    sections.append("*How you actually act - revealed preferences*\n")
    if not behaviors.startswith("No behavioral"):
        sections.append(_extract_content(behaviors))
    else:
        sections.append("\n(Not yet derived from logs)\n")

    # Supporting: Context
    sections.append("\n---\n\n## Context (Supporting)\n")
    sections.append("*Background information - helps with anticipation*\n")

    sections.append("\n### Biographical\n")
    if not biographical.startswith("No biographical"):
        sections.append(_summarize_biographical(biographical))
    else:
        sections.append("(Not yet recorded)\n")

    sections.append("\n### Key Relationships\n")
    if not relationships.startswith("No relationships"):
        sections.append(_summarize_relationships(relationships))
    else:
        sections.append("(Not yet recorded)\n")

    # Assemble final profile
    profile_content = f"""# User Identity Profile

*Consolidated view for agent context - values at the core*

Auto-generated: {timestamp}

{''.join(sections)}
"""

    with open(profile_file, 'w') as f:
        f.write(profile_content)

    return f"Identity profile generated at {timestamp}"


def get_identity_summary() -> str:
    """
    Get a quick summary of the user's identity for agent context.

    This is a condensed version focusing on current values and key facts.

    Returns:
        Brief identity summary
    """
    current_values = get_current_values()
    biographical = get_biographical()

    summary_parts = []

    # Extract name if available
    if not biographical.startswith("No biographical"):
        import re
        name_match = re.search(r'\*\*Name\*\*:\s*(.+)', biographical)
        if name_match and name_match.group(1).strip():
            summary_parts.append(f"**Who**: {name_match.group(1).strip()}")

    # Core values summary
    if not current_values.startswith("No current"):
        summary_parts.append(f"**Current Values**: {_get_first_paragraph(current_values)}")
    else:
        summary_parts.append("**Current Values**: Not yet derived")

    if not summary_parts:
        return "No identity information available yet."

    return "\n\n".join(summary_parts)


def _extract_content(full_text: str) -> str:
    """Extract the main content, removing headers and metadata."""
    lines = full_text.split('\n')
    content_lines = []
    in_content = False

    for line in lines:
        # Skip header lines and metadata
        if line.startswith('#') or line.startswith('*') and line.endswith('*'):
            continue
        if line.startswith('Updated:'):
            in_content = True
            continue
        if in_content:
            content_lines.append(line)

    return '\n'.join(content_lines).strip() + '\n'


def _get_first_paragraph(text: str) -> str:
    """Get the first meaningful paragraph from text."""
    content = _extract_content(text)
    paragraphs = content.split('\n\n')

    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('#') and not p.startswith('---'):
            # Truncate if too long
            if len(p) > 200:
                return p[:200] + "..."
            return p

    return "(See full values)"


def _summarize_biographical(bio: str) -> str:
    """Create a brief summary of biographical info."""
    import re

    lines = []
    fields = ["Name", "Birth Date", "Birth Place", "Current Location"]

    for field in fields:
        match = re.search(rf'\*\*{field}\*\*:\s*(.+)', bio)
        if match and match.group(1).strip():
            lines.append(f"- **{field}**: {match.group(1).strip()}")

    return '\n'.join(lines) + '\n' if lines else "(No basic info recorded)\n"


def _summarize_relationships(rels: str) -> str:
    """Create a brief summary of relationships."""
    import re

    # Find all relationship headers
    matches = re.findall(r'###\s+(\w+):\s+(\w+)', rels)

    if matches:
        lines = [f"- {rel_type}: {name}" for rel_type, name in matches[:5]]
        if len(matches) > 5:
            lines.append(f"- ... and {len(matches) - 5} more")
        return '\n'.join(lines) + '\n'
    else:
        return "(No relationships recorded)\n"


# Tool definitions for the LLM
PROFILE_TOOLS = [
    {
        "name": "get_profile",
        "description": "Read the consolidated identity profile - values at core, behaviors derived, context supporting.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "generate_profile",
        "description": "Regenerate the identity profile from all sources. Call after updating values, behaviors, or context.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_identity_summary",
        "description": "Get a quick summary of the user's identity for context. Useful for quick reference.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handlers mapping
PROFILE_HANDLERS = {
    "get_profile": get_profile,
    "generate_profile": generate_profile,
    "get_identity_summary": get_identity_summary,
}


# Test
if __name__ == "__main__":
    print("Generating profile...")
    print(generate_profile())
    print("\nProfile:")
    print(get_profile())
