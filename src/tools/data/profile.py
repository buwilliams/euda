"""
Profile Tools - Access agent profiles.

Every agent (including user) has a profile at data/agents/{agent_id}/profile.md
Profiles evolve over time based on long-term memory, updated by Synthesis.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .. import tool


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def _get_profile_path(agent_id: str = "user") -> Path:
    """Get path to an agent's profile."""
    return AGENTS_DIR / agent_id / "profile.md"


def _get_historical_profile_path(agent_id: str, year: str) -> Path:
    """Get path to an agent's historical profile for a specific year."""
    return AGENTS_DIR / agent_id / f"profile.{year}.md"


def _ensure_agent_dir(agent_id: str):
    """Ensure agent directory exists."""
    (AGENTS_DIR / agent_id).mkdir(parents=True, exist_ok=True)


@tool("get_profile", "Get an agent's profile containing biographical info, preferences, and patterns. Use when: need to personalize responses or understand context.", tool_type="data")
def get_profile(agent_id: str = "user") -> dict:
    """Get an agent's profile.

    Args:
        agent_id: Agent ID (defaults to "user")
    """
    _ensure_agent_dir(agent_id)

    profile_path = _get_profile_path(agent_id)
    if profile_path.exists():
        return {
            "agent_id": agent_id,
            "content": profile_path.read_text(),
            "exists": True
        }
    return {
        "agent_id": agent_id,
        "content": "",
        "exists": False
    }


@tool("update_profile", "Update an agent's profile with new information. Use when: learning new facts or updating patterns.", tool_type="data")
def update_profile(agent_id: str = "user", content: str = None) -> dict:
    """Update an agent's profile.

    Args:
        agent_id: Agent ID (defaults to "user")
        content: New profile content
    """
    if content is None:
        return {"error": "Content is required"}

    _ensure_agent_dir(agent_id)

    profile_path = _get_profile_path(agent_id)
    profile_path.write_text(content)

    return {"agent_id": agent_id, "status": "updated"}


# Backward-compatible aliases for user-specific operations
@tool("get_user_profile", "Get the user's profile. Use when: need user context. (Alias for get_profile with agent_id='user')", tool_type="data")
def get_user_profile() -> dict:
    """Get the user's profile. Alias for get_profile('user')."""
    return get_profile("user")


@tool("update_user_profile", "Update the user's profile. Use when: learning new facts about the user. (Alias for update_profile with agent_id='user')", tool_type="data")
def update_user_profile(content: str) -> dict:
    """Update the user's profile. Alias for update_profile('user', content)."""
    return update_profile("user", content)


# =============================================================================
# Historical profile helpers (not tools - used by Synthesis)
# =============================================================================

def get_historical_profile(agent_id: str, year: str) -> Optional[str]:
    """Get an agent's historical profile for a specific year.

    Args:
        agent_id: Agent ID
        year: Year (YYYY format)

    Returns:
        Profile content or None if not found
    """
    profile_path = _get_historical_profile_path(agent_id, year)
    if profile_path.exists():
        return profile_path.read_text()
    return None


def save_historical_profile(agent_id: str, year: str, content: str):
    """Save an agent's historical profile for a specific year.

    Args:
        agent_id: Agent ID
        year: Year (YYYY format)
        content: Profile content to save
    """
    _ensure_agent_dir(agent_id)
    profile_path = _get_historical_profile_path(agent_id, year)
    profile_path.write_text(content)


def list_historical_profiles(agent_id: str) -> List[str]:
    """List all available historical profile years for an agent.

    Args:
        agent_id: Agent ID

    Returns:
        List of years (YYYY) with historical profiles, sorted descending
    """
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return []

    years = []
    for path in agent_dir.glob("profile.*.md"):
        # Extract year from filename (profile.YYYY.md)
        year = path.stem.split(".")[-1]
        if year.isdigit() and len(year) == 4:
            years.append(year)

    years.sort(reverse=True)
    return years
