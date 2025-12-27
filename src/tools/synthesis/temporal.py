"""
Temporal Profile tools for the Synthesis Agent (The Keeper).

Tracks who the user is OVER TIME - not just a static snapshot.

Each year produces a temporal profile card capturing:
- Values at that time
- Influences active/discovered that year
- Key beliefs and mental models
- Key relationships and their state
- What changed from the previous year

The evolution view shows how the user has changed across all years.
"""

from datetime import datetime
from pathlib import Path
import re
import json

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
TEMPORAL_DIR = SYNTHESIS_DIR / "state" / "temporal"  # For evolution, timeline
PROFILE_DIR = SYNTHESIS_DIR / "state" / "profile"    # For profiles (contract-compliant)
SHARED_PROFILE_DIR = DATA_DIR / "shared" / "state" / "profile"  # For other agents
LOG_DIR = DATA_DIR / "shared" / "state" / "lifelog"

# Ensure directories exist
TEMPORAL_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
SHARED_PROFILE_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# TEMPORAL PROFILE TOOLS
# =============================================================================

def get_temporal_profile(year: int) -> str:
    """
    Read the temporal profile for a specific year.

    Args:
        year: The year to read profile for

    Returns:
        Profile content or message if not found
    """
    # Check new location first (profile.YYYY.md in profile/)
    profile_file = PROFILE_DIR / f"profile.{year}.md"

    # Fall back to old location for migration (YYYY.profile.md in temporal/)
    if not profile_file.exists():
        old_file = TEMPORAL_DIR / f"{year}.profile.md"
        if old_file.exists():
            profile_file = old_file

    if not profile_file.exists():
        return f"No temporal profile exists for {year}. Use write_temporal_profile to create one."

    with open(profile_file, 'r') as f:
        return f.read()


def write_temporal_profile(year: int, content: str) -> str:
    """
    Write the temporal profile for a specific year.

    The profile should capture who the user was THAT YEAR:
    - Values they held
    - Influences (books, media, thinkers, ideas) discovered or active
    - Key beliefs and mental models
    - Important relationships and their state
    - Major themes and patterns
    - What changed from the previous year

    Args:
        year: The year this profile is for
        content: The profile content in markdown format

    Returns:
        Confirmation message
    """
    # Write to contract-compliant location: profile/profile.YYYY.md
    profile_file = PROFILE_DIR / f"profile.{year}.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# Who I Was in {year}

*Temporal profile card - capturing identity at this point in time*

Generated: {timestamp}

{content}
"""

    with open(profile_file, 'w') as f:
        f.write(full_content)

    # Clean up old location if it exists
    old_file = TEMPORAL_DIR / f"{year}.profile.md"
    if old_file.exists():
        old_file.unlink()

    return f"Temporal profile written for {year}"


def list_temporal_profiles() -> str:
    """
    List all years that have temporal profiles.

    Returns:
        List of years with profiles
    """
    profiles = set()

    # Check new location (profile/profile.YYYY.md)
    for profile_file in PROFILE_DIR.glob("profile.*.md"):
        stem = profile_file.stem
        if stem.startswith("profile.") and not stem.startswith("profile.public"):
            year_str = stem.split('.')[1]
            if year_str.isdigit():
                profiles.add(int(year_str))

    # Check old location for migration (temporal/YYYY.profile.md)
    for profile_file in TEMPORAL_DIR.glob("*.profile.md"):
        year_str = profile_file.stem.split('.')[0]
        if year_str.isdigit():
            profiles.add(int(year_str))

    if not profiles:
        return "No temporal profiles exist yet."

    # Also check which years have summaries but no profile
    years_with_summaries = []
    if LOG_DIR.exists():
        for year_dir in LOG_DIR.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                summary_file = year_dir / "_summary.md"
                if summary_file.exists():
                    years_with_summaries.append(int(year_dir.name))

    missing = set(years_with_summaries) - profiles

    result = "**Temporal profiles:**\n"
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
    evolution_file = TEMPORAL_DIR / "evolution.md"

    if not evolution_file.exists():
        return "No evolution document exists yet. Use write_evolution to create one."

    with open(evolution_file, 'r') as f:
        return f.read()


def write_evolution(content: str) -> str:
    """
    Write the evolution document tracking changes over time.

    This should synthesize all temporal profiles into a narrative of change:
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
    evolution_file = TEMPORAL_DIR / "evolution.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# How I've Evolved

*Tracking the arc of change across all years*

Generated: {timestamp}

{content}
"""

    with open(evolution_file, 'w') as f:
        f.write(full_content)

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
    timeline_file = TEMPORAL_DIR / "influences_timeline.md"

    if not timeline_file.exists():
        return "No influence timeline exists yet."

    with open(timeline_file, 'r') as f:
        return f.read()


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
    timeline_file = TEMPORAL_DIR / "influences_timeline.md"
    timestamp = datetime.now().isoformat()

    # Read existing or create new
    if timeline_file.exists():
        with open(timeline_file, 'r') as f:
            content = f.read()
    else:
        content = f"""# Influence Timeline

*When influences appeared and their impact*

Updated: {timestamp}

"""

    # Update timestamp
    content = re.sub(r'Updated: .*', f'Updated: {timestamp}', content)

    # Add the influence entry
    entry = f"\n## {year}: {item} ({category})\n\n{impact}\n"
    content += entry

    with open(timeline_file, 'w') as f:
        f.write(content)

    return f"Added to timeline: {item} ({year})"


# =============================================================================
# CURRENT PROFILE (from temporal data)
# =============================================================================

def generate_current_profile() -> str:
    """
    Generate the current profile by synthesizing all temporal data.

    Reads all temporal profiles and evolution to create a current snapshot
    that is grounded in the full history. Writes to contract-compliant
    locations and syncs to shared state for other agents.

    Returns:
        The generated current profile content
    """
    # Gather all temporal profiles from both old and new locations
    profiles = []
    years_seen = set()

    # Check new location first (profile/profile.YYYY.md)
    for profile_file in sorted(PROFILE_DIR.glob("profile.*.md")):
        stem = profile_file.stem
        if stem.startswith("profile.") and not stem.startswith("profile.public"):
            year_str = stem.split('.')[1]
            if year_str.isdigit():
                year = int(year_str)
                if year not in years_seen:
                    years_seen.add(year)
                    with open(profile_file, 'r') as f:
                        profiles.append((year, f.read()))

    # Check old location for migration (temporal/YYYY.profile.md)
    for profile_file in sorted(TEMPORAL_DIR.glob("*.profile.md")):
        year_str = profile_file.stem.split('.')[0]
        if year_str.isdigit():
            year = int(year_str)
            if year not in years_seen:
                years_seen.add(year)
                with open(profile_file, 'r') as f:
                    profiles.append((year, f.read()))

    # Sort by year
    profiles.sort(key=lambda x: x[0])

    if not profiles:
        return "No temporal profiles exist. Cannot generate current profile."

    # Get evolution if it exists
    evolution = ""
    evolution_file = TEMPORAL_DIR / "evolution.md"
    if evolution_file.exists():
        with open(evolution_file, 'r') as f:
            evolution = f.read()

    # Get influence timeline if it exists
    timeline = ""
    timeline_file = TEMPORAL_DIR / "influences_timeline.md"
    if timeline_file.exists():
        with open(timeline_file, 'r') as f:
            timeline = f.read()

    # The most recent year's profile is the foundation
    latest_year, latest_profile = profiles[-1]
    timestamp = datetime.now().isoformat()

    result = f"""# Current Profile

*Who I am now - synthesized from {len(profiles)} years of temporal data*

Generated: {timestamp}

## Foundation: {latest_year} Profile

{latest_profile}

"""

    if evolution:
        result += f"""
---

## How I Got Here

{evolution}
"""

    if timeline:
        result += f"""
---

## Influence Timeline

{timeline}
"""

    # Save to contract-compliant location: profile/profile.current.md
    current_file = PROFILE_DIR / "profile.current.md"
    with open(current_file, 'w') as f:
        f.write(result)

    # Sync to shared state for other agents
    shared_file = SHARED_PROFILE_DIR / "profile.current.md"
    with open(shared_file, 'w') as f:
        f.write(result)

    # Clean up old location if it exists
    old_file = SYNTHESIS_DIR / "state" / "derived" / "current_profile.md"
    if old_file.exists():
        old_file.unlink()

    return result


def generate_public_profile() -> str:
    """
    Generate a public profile following redaction.policy.md guidelines.

    Public profiles are structural, not narrative. They describe patterns,
    not events. They point to evidence, never reproduce it. They generalize,
    abstract, and omit rather than expose.

    Returns:
        The generated public profile content
    """
    # First ensure we have a current private profile
    private_file = PROFILE_DIR / "profile.current.md"
    if not private_file.exists():
        # Try to generate it
        generate_current_profile()

    if not private_file.exists():
        return "No private profile exists. Cannot generate public profile."

    with open(private_file, 'r') as f:
        private_content = f.read()

    timestamp = datetime.now().isoformat()
    current_year = datetime.now().year

    # Generate public profile with structural patterns only
    # This is a template - the synthesis agent should refine this
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

    # Save to profile directory
    public_file = PROFILE_DIR / "profile.public.current.md"
    with open(public_file, 'w') as f:
        f.write(public_content)

    # Also save yearly version
    year_file = PROFILE_DIR / f"profile.public.{current_year}.md"
    with open(year_file, 'w') as f:
        f.write(public_content)

    return f"Public profile template generated. The synthesis agent should refine this with actual structural patterns derived from the private profile."


def get_public_profile() -> str:
    """
    Read the current public profile.

    Returns:
        Public profile content or message if not found
    """
    public_file = PROFILE_DIR / "profile.public.current.md"

    if not public_file.exists():
        return "No public profile exists yet. Use generate_public_profile to create one."

    with open(public_file, 'r') as f:
        return f.read()


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

TEMPORAL_TOOLS = [
    # Temporal profile tools
    {
        "name": "get_temporal_profile",
        "description": "Read the temporal profile for a specific year - who the user was at that point in time.",
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
        "description": "Write the temporal profile for a specific year. Should capture values, influences, beliefs, relationships, and changes from previous year.",
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
        "description": "List all years that have temporal profiles and identify gaps.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    # Evolution tools
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
        "description": "Write the evolution narrative synthesizing all temporal profiles into a story of change.",
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
    # Influence timeline tools
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
    # Current profile
    {
        "name": "generate_current_profile",
        "description": "Generate the current profile by synthesizing all temporal data. Saves to profile/ and syncs to shared/state/profile/ for other agents.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    # Public profile
    {
        "name": "generate_public_profile",
        "description": "Generate a public profile following redaction.policy.md guidelines. Creates a template that the synthesis agent should refine.",
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

# Tool handlers mapping
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


# Test
if __name__ == "__main__":
    print(list_temporal_profiles())
