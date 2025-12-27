"""
Private profile management for Synthesis Agent (The Keeper).

Per governance.md, Synthesis Agent has SOLE AUTHORITY to write private profiles.
This module enforces that contract and outputs contract-compliant profiles.

Profile Contract compliance:
- JSON frontmatter
- Canonical section order
- Profile item microformat
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
PROFILE_DIR = SYNTHESIS_DIR / "profile"  # User profile data lives under synthesis

# Ensure directory exists
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# Canonical section order from profile.contract.md
CANONICAL_SECTIONS = [
    "Identity Constraints",
    "Failure Modes",
    "Behavioral Attractors",
    "Utility Tradeoff Curves",
    "Epistemic Style",
    "Narrative Identity",
]


def _build_frontmatter(scope: str = "private", source_profile: Optional[str] = None) -> str:
    """Build JSON frontmatter block."""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    fm = {
        "profile_version": "1.0",
        "scope": scope,
        "generated_at": timestamp,
    }

    if source_profile:
        fm["source_profile"] = source_profile

    return f"```json\n{json.dumps(fm, indent=2)}\n```"


def get_private_profile() -> str:
    """
    Read the current private profile.

    Returns:
        Profile content or message if not found
    """
    profile_file = PROFILE_DIR / "profile.current.md"

    if not profile_file.exists():
        return "No private profile exists yet. Use write_private_profile to create one."

    return profile_file.read_text()


def write_private_profile(
    identity_constraints: str = "",
    failure_modes: str = "",
    behavioral_attractors: str = "",
    utility_tradeoffs: str = "",
    epistemic_style: str = "",
    narrative_identity: str = "",
    _caller_agent: str = "unknown"
) -> str:
    """
    Write the private profile with contract-compliant structure.

    Per governance.md, only Synthesis Agent may call this function.

    Args:
        identity_constraints: Content for Identity Constraints section
        failure_modes: Content for Failure Modes section
        behavioral_attractors: Content for Behavioral Attractors section
        utility_tradeoffs: Content for Utility Tradeoff Curves section
        epistemic_style: Content for Epistemic Style section
        narrative_identity: Content for Narrative Identity section
        _caller_agent: Internal parameter for governance check

    Returns:
        Confirmation message or error
    """
    # Governance check
    if _caller_agent != "synthesis":
        return f"GOVERNANCE VIOLATION: Only Synthesis Agent may write private profiles. Caller: {_caller_agent}"

    # Build profile content
    frontmatter = _build_frontmatter(scope="private")

    sections = []

    # Add sections in canonical order (omit empty ones)
    section_data = [
        ("Identity Constraints", identity_constraints),
        ("Failure Modes", failure_modes),
        ("Behavioral Attractors", behavioral_attractors),
        ("Utility Tradeoff Curves", utility_tradeoffs),
        ("Epistemic Style", epistemic_style),
        ("Narrative Identity", narrative_identity),
    ]

    for section_name, content in section_data:
        if content and content.strip():
            sections.append(f"## {section_name}\n\n{content.strip()}")

    if not sections:
        return "Cannot write empty profile. At least one section must have content."

    # Assemble profile
    profile_content = f"{frontmatter}\n\n# Private Profile\n\n" + "\n\n---\n\n".join(sections) + "\n"

    # Write current profile
    current_file = PROFILE_DIR / "profile.current.md"
    current_file.write_text(profile_content)

    # Write year snapshot
    year = datetime.now().strftime("%Y")
    year_file = PROFILE_DIR / f"profile.{year}.md"
    year_file.write_text(profile_content)

    return f"Private profile written: profile.current.md and profile.{year}.md"


def get_profile_section(section: str) -> str:
    """
    Read a specific section from the current private profile.

    Args:
        section: Section name (e.g., "Identity Constraints")

    Returns:
        Section content or message if not found
    """
    profile = get_private_profile()

    if profile.startswith("No private profile"):
        return profile

    # Find section
    section_header = f"## {section}"
    if section_header not in profile:
        return f"Section '{section}' not found in profile."

    # Extract section content
    start = profile.index(section_header) + len(section_header)

    # Find next section or end
    next_section = None
    for canonical in CANONICAL_SECTIONS:
        header = f"## {canonical}"
        if header in profile[start:]:
            pos = profile.index(header, start)
            if next_section is None or pos < next_section:
                next_section = pos

    if next_section:
        content = profile[start:next_section]
    else:
        content = profile[start:]

    # Clean up separators
    content = content.replace("---", "").strip()

    return content if content else f"Section '{section}' is empty."


# Tool definitions for Synthesis Agent
PRIVATE_PROFILE_TOOLS = [
    {
        "name": "get_private_profile",
        "description": "Read the current private profile.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_private_profile",
        "description": """Write the private profile with contract-compliant structure.
Only Synthesis Agent may call this function (governance enforced).

Provide content for each section. Empty sections will be omitted.
Use the profile item microformat where applicable:
- **[Label]**: [Description]
  - Evidence: [pointer to source]
  - Confidence: [high | medium | low]
  - Last observed: [YYYY or YYYY-MM]""",
        "input_schema": {
            "type": "object",
            "properties": {
                "identity_constraints": {
                    "type": "string",
                    "description": "Non-negotiable rules revealed by sacrifice and refusal"
                },
                "failure_modes": {
                    "type": "string",
                    "description": "Predictable breakdowns under stress"
                },
                "behavioral_attractors": {
                    "type": "string",
                    "description": "Stable patterns across contexts"
                },
                "utility_tradeoffs": {
                    "type": "string",
                    "description": "What gets sacrificed first when goals conflict"
                },
                "epistemic_style": {
                    "type": "string",
                    "description": "How uncertainty, revision, and authority are handled"
                },
                "narrative_identity": {
                    "type": "string",
                    "description": "Self-concept and aspirational framing"
                }
            }
        }
    },
    {
        "name": "get_profile_section",
        "description": "Read a specific section from the current private profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": CANONICAL_SECTIONS,
                    "description": "Section name to read"
                }
            },
            "required": ["section"]
        }
    }
]

# Handlers with governance wrapper
def _make_governed_handler(func, agent_name: str):
    """Wrap handler to inject caller agent for governance checks."""
    def wrapper(**kwargs):
        if "_caller_agent" in func.__code__.co_varnames:
            kwargs["_caller_agent"] = agent_name
        return func(**kwargs)
    return wrapper


def get_handlers_for_agent(agent_name: str) -> dict:
    """
    Get handlers configured for a specific agent.

    This enforces governance by injecting the caller identity.
    """
    return {
        "get_private_profile": get_private_profile,
        "write_private_profile": _make_governed_handler(write_private_profile, agent_name),
        "get_profile_section": get_profile_section,
    }


# Default handlers (for Synthesis)
PRIVATE_PROFILE_HANDLERS = get_handlers_for_agent("synthesis")


if __name__ == "__main__":
    # Test
    print("Testing private profile tools...")

    # Test write (as synthesis)
    result = write_private_profile(
        identity_constraints="- **Family first**: Will not sacrifice family time for work\n  - Evidence: lifelog/2024/\n  - Confidence: high\n  - Last observed: 2024-12",
        failure_modes="- **Withdrawal under stress**: Retreats to solitude when overwhelmed\n  - Evidence: lifelog/2024/\n  - Confidence: high\n  - Last observed: 2024-11",
        _caller_agent="synthesis"
    )
    print(result)

    print("\nProfile content:")
    print(get_private_profile())

    # Test governance violation
    print("\nTesting governance violation:")
    result = write_private_profile(
        identity_constraints="Test",
        _caller_agent="interaction"
    )
    print(result)
