"""
Profile tools for the Synthesis Agent (The Keeper).

The profile consolidates all identity facets into a single view for other agents.
It emphasizes EPISTEMIC AXIOMS at the foundation, with values and behaviors derived.

Hierarchy:
1. Epistemic (foundational) - axioms, mental models, tools (with provenance)
2. Values (derived from epistemic core)
3. Behaviors (reveals operative axioms)
4. Context (supporting) - biographical, relationships
"""

from datetime import datetime
from pathlib import Path

# Import from sibling modules
from .epistemic import get_axioms, get_mental_models, get_epistemic_tools
from .values import get_current_values, get_phase_values, get_lifetime_values
from .behaviors import get_behaviors
from .context import get_biographical, get_relationships, get_influences

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
DERIVED_DIR = SYNTHESIS_DIR / "state" / "derived"

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

    The profile emphasizes epistemic axioms at the foundation, with values
    and behaviors derived from them.

    Returns:
        Confirmation message with summary
    """
    profile_file = DERIVED_DIR / "profile.md"
    timestamp = datetime.now().isoformat()

    # Gather all identity data
    axioms = get_axioms()
    mental_models = get_mental_models()
    epistemic_tools = get_epistemic_tools()
    current_values = get_current_values()
    phase_values = get_phase_values()
    lifetime_values = get_lifetime_values()
    behaviors = get_behaviors()
    biographical = get_biographical()
    relationships = get_relationships()
    influences = get_influences()

    # Build the profile with epistemic core at the foundation
    sections = []

    # Foundation: Epistemic Core
    sections.append("## Epistemic Core (Foundation)\n")
    sections.append("*The beliefs and reasoning patterns that generate values and drive behavior*\n")
    sections.append("*Each entry includes the behavior that revealed it*\n")

    if not axioms.startswith("No epistemic"):
        sections.append("\n### Axioms\n")
        sections.append("*Foundational beliefs about reality*\n")
        sections.append(_extract_content(axioms))

    if not mental_models.startswith("No mental"):
        sections.append("\n### Mental Models\n")
        sections.append("*Frameworks used for thinking*\n")
        sections.append(_extract_content(mental_models))

    if not epistemic_tools.startswith("No epistemic"):
        sections.append("\n### Epistemic Tools\n")
        sections.append("*Reasoning methods employed*\n")
        sections.append(_extract_content(epistemic_tools))

    if axioms.startswith("No") and mental_models.startswith("No") and epistemic_tools.startswith("No"):
        sections.append("\n(Not yet derived - run derive to uncover the mind behind behaviors)\n")

    # Derived: Values
    sections.append("\n---\n\n## Values (Derived from Epistemic Core)\n")
    sections.append("*What you care about - emergent from foundational beliefs*\n")

    if not current_values.startswith("No current"):
        sections.append("\n### Current Focus\n")
        sections.append(_extract_content(current_values))

    if not lifetime_values.startswith("No lifetime"):
        sections.append("\n### Enduring Values\n")
        sections.append(_extract_content(lifetime_values))

    if not phase_values.startswith("No phase"):
        sections.append("\n### Life Phase Values\n")
        sections.append(_extract_content(phase_values))

    # Reveals: Behaviors
    sections.append("\n---\n\n## Behavioral Patterns (Reveals Operative Axioms)\n")
    sections.append("*How you actually act - shows which beliefs are truly held*\n")
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

    sections.append("\n### Influences\n")
    sections.append("*Books, media, thinkers, ideas, places that shaped thinking*\n")
    if not influences.startswith("No influences"):
        sections.append(_extract_content(influences))
    else:
        sections.append("(Not yet recorded)\n")

    # Assemble final profile
    profile_content = f"""# User Identity Profile

*Consolidated view for agent context - epistemic core at the foundation*

Auto-generated: {timestamp}

{''.join(sections)}
"""

    with open(profile_file, 'w') as f:
        f.write(profile_content)

    return f"Identity profile generated at {timestamp}"


def get_synthesis_summary() -> str:
    """
    Get a quick summary of the user's identity for agent context.

    This is a condensed version focusing on epistemic core and current values.

    Returns:
        Brief identity summary
    """
    axioms = get_axioms()
    current_values = get_current_values()
    biographical = get_biographical()

    summary_parts = []

    # Extract name if available
    if not biographical.startswith("No biographical"):
        import re
        name_match = re.search(r'\*\*Name\*\*:\s*(.+)', biographical)
        if name_match and name_match.group(1).strip():
            summary_parts.append(f"**Who**: {name_match.group(1).strip()}")

    # Epistemic foundation summary
    if not axioms.startswith("No epistemic"):
        summary_parts.append(f"**Epistemic Foundation**: {_get_first_paragraph(axioms)}")

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

    return "(See full profile)"


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
        "description": "Read the consolidated identity profile - epistemic core at foundation, values derived, behaviors revealing.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "generate_profile",
        "description": "Regenerate the identity profile from all sources. Call after updating epistemic, values, behaviors, or context.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_synthesis_summary",
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
    "get_synthesis_summary": get_synthesis_summary,
}

# Test
if __name__ == "__main__":
    print("Generating profile...")
    print(generate_profile())
    print("\nProfile:")
    print(get_profile())
