"""
Identity Tools - Access agent identities.

Every agent (including user) has an identity at data/agents/{agent_id}/identity.md
Identities evolve over time based on long-term memory, updated by Reflection.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional



DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"

def _normalize_identity_content(content: str) -> str:
    """Normalize escaped newlines to real newlines for markdown rendering."""
    if content is None:
        return ""
    normalized = content.replace("\\r\\n", "\n")
    normalized = normalized.replace("\\n", "\n")
    return normalized


def _get_identity_path(agent_id: str = "user") -> Path:
    """Get path to an agent's identity."""
    return AGENTS_DIR / agent_id / "identity.md"


def _get_historical_identity_path(agent_id: str, year: str) -> Path:
    """Get path to an agent's historical identity for a specific year."""
    return AGENTS_DIR / agent_id / f"identity.{year}.md"


def _ensure_agent_dir(agent_id: str):
    """Ensure agent directory exists."""
    (AGENTS_DIR / agent_id).mkdir(parents=True, exist_ok=True)


def get_identity(agent_id: str = "user") -> dict:
    """Get an agent's identity.

    Args:
        agent_id: Agent ID (defaults to "user")
    """
    _ensure_agent_dir(agent_id)

    identity_path = _get_identity_path(agent_id)
    if identity_path.exists():
        raw = identity_path.read_text()
        normalized = _normalize_identity_content(raw)
        if normalized != raw:
            identity_path.write_text(normalized)
        return {
            "agent_id": agent_id,
            "content": normalized,
            "exists": True
        }
    return {
        "agent_id": agent_id,
        "content": "",
        "exists": False
    }


def update_identity(agent_id: str = "user", content: str = None) -> dict:
    """Update an agent's identity.

    Args:
        agent_id: Agent ID (defaults to "user")
        content: New identity content
    """
    if content is None:
        return {"error": "Content is required"}

    _ensure_agent_dir(agent_id)

    identity_path = _get_identity_path(agent_id)
    identity_path.write_text(_normalize_identity_content(content))

    return {"agent_id": agent_id, "status": "updated"}


# Backward-compatible aliases for user-specific operations
def get_user_identity() -> dict:
    """Get the user's identity. Alias for get_identity('user')."""
    return get_identity("user")


def update_user_identity(content: str) -> dict:
    """Update the user's identity. Alias for update_identity('user', content)."""
    return update_identity("user", content)


# =============================================================================
# Historical identity helpers (not tools - used by Reflection)
# =============================================================================

def get_historical_identity(agent_id: str, year: str) -> Optional[str]:
    """Get an agent's historical identity for a specific year.

    Args:
        agent_id: Agent ID
        year: Year (YYYY format)

    Returns:
        Identity content or None if not found
    """
    identity_path = _get_historical_identity_path(agent_id, year)
    if identity_path.exists():
        return identity_path.read_text()
    return None


def save_historical_identity(agent_id: str, year: str, content: str):
    """Save an agent's historical identity for a specific year.

    Args:
        agent_id: Agent ID
        year: Year (YYYY format)
        content: Identity content to save
    """
    _ensure_agent_dir(agent_id)
    identity_path = _get_historical_identity_path(agent_id, year)
    identity_path.write_text(_normalize_identity_content(content))


def list_historical_identities(agent_id: str) -> List[str]:
    """List all available historical identity years for an agent.

    Args:
        agent_id: Agent ID

    Returns:
        List of years (YYYY) with historical identities, sorted descending
    """
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return []

    years = []
    for path in agent_dir.glob("identity.*.md"):
        # Extract year from filename (identity.YYYY.md)
        year = path.stem.split(".")[-1]
        if year.isdigit() and len(year) == 4:
            years.append(year)

    years.sort(reverse=True)
    return years
