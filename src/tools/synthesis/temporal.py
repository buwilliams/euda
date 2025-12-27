"""
Profile tools for the Synthesis Agent (The Keeper).

Manages yearly profiles and evolution tracking.

Each year produces a profile capturing:
- Behavioral model (identity constraints, failure modes, attractors, tradeoffs, epistemic style)
- Biographical context (values, influences, beliefs, relationships)

The evolution view shows how the user has changed across all years.
"""

from datetime import datetime
from pathlib import Path
import re

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
PROFILE_DIR = SYNTHESIS_DIR / "state" / "profile"
SHARED_PROFILE_DIR = DATA_DIR / "shared" / "state" / "profile"
LOG_DIR = DATA_DIR / "shared" / "state" / "lifelog"

# Ensure directories exist
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
SHARED_PROFILE_DIR.mkdir(parents=True, exist_ok=True)


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
    profile_file = PROFILE_DIR / f"profile.{year}.md"

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
    profile_file = PROFILE_DIR / f"profile.{year}.md"
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

    for profile_file in PROFILE_DIR.glob("profile.*.md"):
        stem = profile_file.stem
        if stem.startswith("profile.") and not stem.startswith("profile.public") and stem != "profile.current":
            year_str = stem.split('.')[1]
            if year_str.isdigit():
                profiles.add(int(year_str))

    if not profiles:
        return "No profiles exist yet."

    # Check which years have summaries but no profile
    years_with_summaries = []
    if LOG_DIR.exists():
        for year_dir in LOG_DIR.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                summary_file = year_dir / "_summary.md"
                if summary_file.exists():
                    years_with_summaries.append(int(year_dir.name))

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
    evolution_file = PROFILE_DIR / "evolution.md"

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
    evolution_file = PROFILE_DIR / "evolution.md"
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
    timeline_file = PROFILE_DIR / "influences_timeline.md"

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
    timeline_file = PROFILE_DIR / "influences_timeline.md"
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

    Reads the most recent profile.YYYY.md and uses it as the current profile.
    For multi-year data, includes evolution narrative.

    Writes to profile.current.md and syncs to shared state.

    Returns:
        The generated current profile content
    """
    timestamp = datetime.now().isoformat()

    # Gather all yearly profiles
    profiles = []

    for profile_file in sorted(PROFILE_DIR.glob("profile.*.md")):
        stem = profile_file.stem
        if stem.startswith("profile.") and not stem.startswith("profile.public") and stem != "profile.current":
            year_str = stem.split('.')[1]
            if year_str.isdigit():
                year = int(year_str)
                profiles.append((year, profile_file.read_text()))

    profiles.sort(key=lambda x: x[0])

    if not profiles:
        return "No profiles exist. Run 'derive' to generate profiles."

    # Get evolution if exists
    evolution = ""
    evolution_file = PROFILE_DIR / "evolution.md"
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

    # Save to profile directory
    current_file = PROFILE_DIR / "profile.current.md"
    current_file.write_text(result)

    # Sync to shared state for other agents
    shared_file = SHARED_PROFILE_DIR / "profile.current.md"
    shared_file.write_text(result)

    return result


def generate_public_profile() -> str:
    """
    Generate a public profile following redaction.policy.md guidelines.

    Public profiles are structural, not narrative. They describe patterns,
    not events. They point to evidence, never reproduce it.

    Returns:
        The generated public profile content
    """
    private_file = PROFILE_DIR / "profile.current.md"
    if not private_file.exists():
        generate_current_profile()

    if not private_file.exists():
        return "No private profile exists. Cannot generate public profile."

    timestamp = datetime.now().isoformat()
    current_year = datetime.now().year

    public_content = f'''```json
{{
  "profile_version": "1.0",
  "scope": "public",
  "generated_at": "{timestamp}",
  "source_profile": "profile/profile.current.md"
}}
```

# Public Profile

*Structural patterns for alignment and collaboration*

Generated: {timestamp}

## Identity Constraints

*Non-negotiable rules revealed by sacrifice and refusal*

(To be derived from private profile by synthesis agent)

## Behavioral Attractors

*Stable patterns across contexts*

(To be derived from private profile by synthesis agent)

## Epistemic Style

*How uncertainty, revision, and authority are handled*

(To be derived from private profile by synthesis agent)

## Narrative Identity

*Self-concept and aspirational framing*

(To be derived from private profile by synthesis agent)

---

*This public profile follows redaction.policy.md guidelines: structural over narrative, patterns over events, omission over exposure.*
'''

    public_file = PROFILE_DIR / "profile.public.current.md"
    public_file.write_text(public_content)

    year_file = PROFILE_DIR / f"profile.public.{current_year}.md"
    year_file.write_text(public_content)

    return "Public profile template generated."


def get_public_profile() -> str:
    """
    Read the current public profile.

    Returns:
        Public profile content or message if not found
    """
    public_file = PROFILE_DIR / "profile.public.current.md"

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
