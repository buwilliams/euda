"""
Profile tools for the Profiler Agent.

Manages yearly profiles and evolution tracking.

Each year produces a profile capturing:
- Behavioral model (identity constraints, failure modes, attractors, tradeoffs, epistemic style)
- Biographical context (values, influences, beliefs, relationships)

Profiles are stored in the lifelog alongside the data they're derived from:
- lifelog/YYYY/_profile.md - yearly profile
- lifelog/_profile.current.md - current synthesized profile
- lifelog/_profile.public.md - public profile

The evolution view shows how the user has changed across all years.
"""

from datetime import datetime
from pathlib import Path
import re

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SRC_DIR = Path(__file__).parent.parent.parent
LIFELOG_DIR = DATA_DIR / "shared" / "state" / "lifelog"
CONTRACTS_DIR = SRC_DIR / "agents" / "contracts"  # Profile contract and policy (in codebase)

# Ensure directories exist
LIFELOG_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# YEARLY PROFILE TOOLS
# =============================================================================

def get_temporal_profile(year: int) -> str:
    """
    Read the profile for a specific year.

    Args:
        year: The year to read profile for

    Returns:
        Profile content or message if not found
    """
    year_dir = LIFELOG_DIR / str(year)
    profile_file = year_dir / "_profile.md"

    if not profile_file.exists():
        return f"No profile exists for {year}."

    return profile_file.read_text()


def write_temporal_profile(year: int, content: str) -> str:
    """
    Write biographical content for a specific year.

    This captures raw biographical data that will be synthesized into
    the full profile by the extraction step.

    Args:
        year: The year this profile is for
        content: The biographical content in markdown format

    Returns:
        Confirmation message
    """
    year_dir = LIFELOG_DIR / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    profile_file = year_dir / "_profile.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# Profile {year}

*Who I was in {year}*

Generated: {timestamp}

{content}
"""

    profile_file.write_text(full_content)
    return f"Profile written for {year}"


def list_temporal_profiles() -> str:
    """
    List all years that have profiles.

    Returns:
        List of years with profiles
    """
    profiles = set()
    years_with_summaries = []

    # Scan lifelog year directories
    if LIFELOG_DIR.exists():
        for year_dir in LIFELOG_DIR.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                year = int(year_dir.name)
                profile_file = year_dir / "_profile.md"
                summary_file = year_dir / "_summary.md"

                if profile_file.exists():
                    profiles.add(year)
                if summary_file.exists():
                    years_with_summaries.append(year)

    if not profiles:
        return "No profiles exist yet."

    missing = set(years_with_summaries) - profiles

    result = "**Profiles:**\n"
    for year in sorted(profiles):
        result += f"- {year}: ✓ profile exists\n"

    if missing:
        result += "\n**Years with summaries but no profile:**\n"
        for year in sorted(missing):
            result += f"- {year}: needs profile\n"

    return result


# =============================================================================
# EVOLUTION TRACKING
# =============================================================================

def get_evolution() -> str:
    """
    Read the evolution document showing how the user changed over time.

    Returns:
        Evolution content or message if not found
    """
    evolution_file = LIFELOG_DIR / "_evolution.md"

    if not evolution_file.exists():
        return "No evolution document exists yet."

    return evolution_file.read_text()


def write_evolution(content: str) -> str:
    """
    Write the evolution document tracking changes over time.

    This should synthesize all profiles into a narrative of change:
    - How values evolved (what emerged, what faded, what stayed constant)
    - When key influences appeared and their lasting impact
    - How beliefs and mental models shifted
    - Relationship patterns over time
    - Major life phases and transitions

    Args:
        content: The evolution narrative in markdown format

    Returns:
        Confirmation message
    """
    evolution_file = LIFELOG_DIR / "_evolution.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# How I've Evolved

*Tracking the arc of change across all years*

Generated: {timestamp}

{content}
"""

    evolution_file.write_text(full_content)
    return "Evolution document written"


# =============================================================================
# INFLUENCE TIMELINE
# =============================================================================

def get_influence_timeline() -> str:
    """
    Read the influence timeline showing when influences appeared.

    Returns:
        Timeline content or message if not found
    """
    timeline_file = LIFELOG_DIR / "_influences.md"

    if not timeline_file.exists():
        return "No influence timeline exists yet."

    return timeline_file.read_text()


def add_influence_to_timeline(year: int, category: str, item: str, impact: str) -> str:
    """
    Add an influence to the timeline.

    Args:
        year: When this influence was discovered/active
        category: Type (Books, Media, Thinkers, Ideas, Places)
        item: The specific influence
        impact: How it shaped thinking

    Returns:
        Confirmation message
    """
    timeline_file = LIFELOG_DIR / "_influences.md"
    timestamp = datetime.now().isoformat()

    if timeline_file.exists():
        content = timeline_file.read_text()
        content = re.sub(r'Updated: .*', f'Updated: {timestamp}', content)
    else:
        content = f"""# Influence Timeline

*When influences appeared and their impact*

Updated: {timestamp}

"""

    entry = f"\n## {year}: {item} ({category})\n\n{impact}\n"
    content += entry

    timeline_file.write_text(content)
    return f"Added to timeline: {item} ({year})"


# =============================================================================
# CURRENT PROFILE
# =============================================================================

def generate_current_profile() -> str:
    """
    Generate the current profile from yearly profiles.

    Reads yearly _profile.md files from each year directory and synthesizes
    into a current profile. For multi-year data, includes evolution narrative.

    Writes to lifelog/_profile.current.md

    Returns:
        The generated current profile content
    """
    timestamp = datetime.now().isoformat()

    # Gather all yearly profiles from lifelog year directories
    profiles = []

    if LIFELOG_DIR.exists():
        for year_dir in sorted(LIFELOG_DIR.iterdir()):
            if year_dir.is_dir() and year_dir.name.isdigit():
                profile_file = year_dir / "_profile.md"
                if profile_file.exists():
                    year = int(year_dir.name)
                    profiles.append((year, profile_file.read_text()))

    profiles.sort(key=lambda x: x[0])

    if not profiles:
        return "No profiles exist. Run 'derive' to generate profiles."

    # Get evolution if exists
    evolution = ""
    evolution_file = LIFELOG_DIR / "_evolution.md"
    if evolution_file.exists():
        evolution = evolution_file.read_text()

    # Build current profile from most recent year
    latest_year, latest_profile = profiles[-1]

    result = f"""# Current Profile

*Who I am now - based on {len(profiles)} year(s) of data*

Generated: {timestamp}

{latest_profile}
"""

    if evolution and len(profiles) > 1:
        result += f"""
---

## Evolution

{evolution}
"""

    # Save to lifelog root
    current_file = LIFELOG_DIR / "_profile.current.md"
    current_file.write_text(result)

    return result


def generate_public_profile() -> str:
    """
    Generate a public profile following redaction.policy.md guidelines.

    Public profiles are structural, not narrative. They describe patterns,
    not events. They point to evidence, never reproduce it.

    Returns:
        The generated public profile content
    """
    private_file = LIFELOG_DIR / "_profile.current.md"
    if not private_file.exists():
        generate_current_profile()

    if not private_file.exists():
        return "No private profile exists. Cannot generate public profile."

    timestamp = datetime.now().isoformat()

    public_content = f'''```json
{{
  "profile_version": "1.0",
  "scope": "public",
  "generated_at": "{timestamp}",
  "source_profile": "lifelog/_profile.current.md"
}}
```

# Public Profile

*Structural patterns for alignment and collaboration*

Generated: {timestamp}

## Identity Constraints

*Non-negotiable rules revealed by sacrifice and refusal*

(To be derived from private profile by profiler agent)

## Behavioral Attractors

*Stable patterns across contexts*

(To be derived from private profile by profiler agent)

## Epistemic Style

*How uncertainty, revision, and authority are handled*

(To be derived from private profile by profiler agent)

## Narrative Identity

*Self-concept and aspirational framing*

(To be derived from private profile by profiler agent)

---

*This public profile follows redaction.policy.md guidelines: structural over narrative, patterns over events, omission over exposure.*
'''

    public_file = LIFELOG_DIR / "_profile.public.md"
    public_file.write_text(public_content)

    return "Public profile template generated."


def get_public_profile() -> str:
    """
    Read the current public profile.

    Returns:
        Public profile content or message if not found
    """
    public_file = LIFELOG_DIR / "_profile.public.md"

    if not public_file.exists():
        return "No public profile exists yet."

    return public_file.read_text()


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

TEMPORAL_TOOLS = [
    {
        "name": "get_temporal_profile",
        "description": "Read the profile for a specific year.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year to read profile for"
                }
            },
            "required": ["year"]
        }
    },
    {
        "name": "write_temporal_profile",
        "description": "Write the profile for a specific year. Should capture values, influences, beliefs, relationships, and changes from previous year.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year this profile is for"
                },
                "content": {
                    "type": "string",
                    "description": "The profile content in markdown format"
                }
            },
            "required": ["year", "content"]
        }
    },
    {
        "name": "list_temporal_profiles",
        "description": "List all years that have profiles and identify gaps.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_evolution",
        "description": "Read the evolution document showing how the user changed over time.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_evolution",
        "description": "Write the evolution narrative synthesizing all profiles into a story of change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The evolution narrative in markdown format"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "get_influence_timeline",
        "description": "Read the influence timeline showing when books, media, thinkers, ideas, places appeared.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "add_influence_to_timeline",
        "description": "Add an influence to the timeline with the year it was discovered.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "When this influence was discovered/active"
                },
                "category": {
                    "type": "string",
                    "description": "Type: Books, Media, Thinkers, Ideas, Places"
                },
                "item": {
                    "type": "string",
                    "description": "The specific influence"
                },
                "impact": {
                    "type": "string",
                    "description": "How it shaped thinking"
                }
            },
            "required": ["year", "category", "item", "impact"]
        }
    },
    {
        "name": "generate_current_profile",
        "description": "Generate the current profile from yearly profiles. Syncs to shared state for other agents.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "generate_public_profile",
        "description": "Generate a public profile following redaction.policy.md guidelines.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_public_profile",
        "description": "Read the current public profile.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

TEMPORAL_HANDLERS = {
    "get_temporal_profile": get_temporal_profile,
    "write_temporal_profile": write_temporal_profile,
    "list_temporal_profiles": list_temporal_profiles,
    "get_evolution": get_evolution,
    "write_evolution": write_evolution,
    "get_influence_timeline": get_influence_timeline,
    "add_influence_to_timeline": add_influence_to_timeline,
    "generate_current_profile": generate_current_profile,
    "generate_public_profile": generate_public_profile,
    "get_public_profile": get_public_profile,
}
