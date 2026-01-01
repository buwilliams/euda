"""
Private profile management for the Profiler Agent.

Per governance.md, Profiler Agent has SOLE AUTHORITY to write private profiles.
This module enforces that contract and outputs contract-compliant profiles.

Profiles are stored in the lifelog:
- lifelog/_profile.current.md - current private profile
- lifelog/YYYY/_profile.md - yearly profiles

Profile schema (from docs/2_profile.md):
1. Biographical Information
2. Wants and Fears
3. Stable Attractors
4. Notable Events and Actions
5. Influences
6. Interests
7. Summary of Changes
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
LIFELOG_DIR = DATA_DIR / "shared" / "state" / "lifelog"

# Ensure directory exists
LIFELOG_DIR.mkdir(parents=True, exist_ok=True)

# Canonical section order from docs/2_profile.md
CANONICAL_SECTIONS = [
    "Biographical Information",
    "Wants and Fears",
    "Stable Attractors",
    "Notable Events and Actions",
    "Influences",
    "Interests",
    "Summary of Changes",
]


def _build_frontmatter(scope: str = "private", source_profile: Optional[str] = None) -> str:
    """Build JSON frontmatter block."""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    fm = {
        "profile_version": "2.0",
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
    profile_file = LIFELOG_DIR / "_profile.current.md"

    if not profile_file.exists():
        return "No private profile exists yet. Use write_private_profile to create one."

    return profile_file.read_text()


def write_private_profile(
    biographical_info: str = "",
    wants_and_fears: str = "",
    stable_attractors: str = "",
    notable_events: str = "",
    influences: str = "",
    interests: str = "",
    changes_summary: str = "",
    _caller_agent: str = "unknown"
) -> str:
    """
    Write the private profile with contract-compliant structure.

    Per governance.md, only Profiler Agent may call this function.

    Args:
        biographical_info: Name, location, occupation, family, key dates
        wants_and_fears: Patterns revealing what person pursues and avoids
        stable_attractors: Patterns the person returns to across time/context
        notable_events: Significant events (consistent or surprising)
        influences: People, ideas, places, activities that shaped them
        interests: Current goals, projects, work, hobbies
        changes_summary: How they've evolved from previous years
        _caller_agent: Internal parameter for governance check

    Returns:
        Confirmation message or error
    """
    # Governance check
    if _caller_agent != "profiler":
        return f"GOVERNANCE VIOLATION: Only Profiler Agent may write private profiles. Caller: {_caller_agent}"

    # Build profile content
    frontmatter = _build_frontmatter(scope="private")

    sections = []

    # Add sections in canonical order (omit empty ones)
    section_data = [
        ("Biographical Information", biographical_info),
        ("Wants and Fears", wants_and_fears),
        ("Stable Attractors", stable_attractors),
        ("Notable Events and Actions", notable_events),
        ("Influences", influences),
        ("Interests", interests),
        ("Summary of Changes", changes_summary),
    ]

    for section_name, content in section_data:
        if content and content.strip():
            sections.append(f"## {section_name}\n\n{content.strip()}")

    if not sections:
        return "Cannot write empty profile. At least one section must have content."

    # Assemble profile
    profile_content = f"{frontmatter}\n\n# Private Profile\n\n" + "\n\n---\n\n".join(sections) + "\n"

    # Write current profile to lifelog root
    current_file = LIFELOG_DIR / "_profile.current.md"
    current_file.write_text(profile_content)

    # Write year snapshot to year directory
    year = datetime.now().strftime("%Y")
    year_dir = LIFELOG_DIR / year
    year_dir.mkdir(parents=True, exist_ok=True)
    year_file = year_dir / "_profile.md"
    year_file.write_text(profile_content)

    return f"Private profile written: _profile.current.md and {year}/_profile.md"


def get_profile_section(section: str) -> str:
    """
    Read a specific section from the current private profile.

    Args:
        section: Section name (e.g., "Stable Attractors")

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


# Tool definitions for Profiler Agent
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
        "description": """Write the private profile following the schema from docs/2_profile.md.
Only Profiler Agent may call this function (governance enforced).

Provide content for each section. Empty sections will be omitted.
Use evidence citations and confidence levels where applicable:
- **[Item]**: [Description]
  - Evidence: [pointer to source]
  - Confidence: [high | medium | low]""",
        "input_schema": {
            "type": "object",
            "properties": {
                "biographical_info": {
                    "type": "string",
                    "description": "Name, location, occupation, family structure, key dates"
                },
                "wants_and_fears": {
                    "type": "string",
                    "description": "Patterns of behavior revealing what person pursues (wants) and avoids (fears)"
                },
                "stable_attractors": {
                    "type": "string",
                    "description": "Patterns the person returns to across time and context, especially under stress"
                },
                "notable_events": {
                    "type": "string",
                    "description": "Significant events - either consistent with patterns or surprising departures"
                },
                "influences": {
                    "type": "string",
                    "description": "People, ideas, books, places, activities, experiences that shaped them"
                },
                "interests": {
                    "type": "string",
                    "description": "Current goals, projects, work, hobbies, entertainment"
                },
                "changes_summary": {
                    "type": "string",
                    "description": "How they've evolved from previous years - what emerged, faded, stayed constant"
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


# Default handlers (for Profiler)
PRIVATE_PROFILE_HANDLERS = get_handlers_for_agent("profiler")


if __name__ == "__main__":
    # Test
    print("Testing private profile tools...")

    # Test write (as profiler)
    result = write_private_profile(
        biographical_info="- **Name**: Test User\n- **Location**: Atlanta, GA",
        wants_and_fears="**Wants**\n- **Stability**: Seeks predictable routines\n  - Evidence: lifelog/2024/\n  - Confidence: high",
        stable_attractors="- **Problem-solving retreat**: Returns to solo analysis when stressed\n  - Domain: intellectual\n  - Evidence: lifelog/2024/\n  - Confidence: high",
        _caller_agent="profiler"
    )
    print(result)

    print("\nProfile content:")
    print(get_private_profile())

    # Test governance violation
    print("\nTesting governance violation:")
    result = write_private_profile(
        biographical_info="Test",
        _caller_agent="friend"
    )
    print(result)
