"""
Profile tools for the Synthesis Agent (The Keeper).

The profile is generated from temporal profiles via generate_current_profile()
in temporal.py. This module provides read access to the consolidated profile.
"""

from pathlib import Path

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
PROFILE_DIR = SYNTHESIS_DIR / "state" / "profile"
SHARED_PROFILE_DIR = DATA_DIR / "shared" / "state" / "profile"

# Ensure directories exist
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
SHARED_PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def get_profile() -> str:
    """
    Read the consolidated identity profile.

    Returns:
        Profile content or message if not found
    """
    # Check for current profile first
    profile_file = PROFILE_DIR / "profile.current.md"

    # Fall back to legacy profile.md
    if not profile_file.exists():
        profile_file = PROFILE_DIR / "profile.md"

    if not profile_file.exists():
        return "No identity profile generated yet. Use generate_current_profile() from temporal tools."

    with open(profile_file, 'r') as f:
        return f.read()


def get_synthesis_summary() -> str:
    """
    Get a quick summary of the user's identity for agent context.

    Returns:
        Brief identity summary or message if no profile exists
    """
    profile = get_profile()

    if profile.startswith("No identity profile"):
        return "No identity information available yet."

    # Extract first few sections as summary
    lines = profile.split('\n')
    summary_lines = []
    line_count = 0

    for line in lines:
        summary_lines.append(line)
        line_count += 1
        # Stop after about 30 lines or first major section break
        if line_count > 30 or (line_count > 10 and line.startswith('---')):
            break

    return '\n'.join(summary_lines) + "\n\n(See full profile for more)"


# Tool definitions for the LLM
PROFILE_TOOLS = [
    {
        "name": "get_profile",
        "description": "Read the consolidated identity profile.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_synthesis_summary",
        "description": "Get a quick summary of the user's identity for context.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handlers mapping
PROFILE_HANDLERS = {
    "get_profile": get_profile,
    "get_synthesis_summary": get_synthesis_summary,
}
