"""
Identity Module - Agent identity loading and management.

Identity is the "who am I?" aspect of an agent:
- Purpose: What the agent exists to do
- Values: What the agent prioritizes
- Voice: How the agent communicates
- Stable attractors: Persistent characteristics

Identity is stored in data/agents/{id}/identity.md
"""

import json
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def load_config(agent_id: str) -> dict:
    """Load agent configuration from disk.

    Args:
        agent_id: The agent's ID

    Returns:
        Agent configuration dict
    """
    config_path = AGENTS_DIR / agent_id / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {
        "id": agent_id,
        "name": agent_id.title(),
        "state": "enabled",
        "tools": [],
        "triggers": ["topic:assigned"]
    }


def load_identity(agent_id: str, config: Optional[dict] = None) -> str:
    """Load agent identity from disk.

    Args:
        agent_id: The agent's ID
        config: Optional config dict (for default name)

    Returns:
        Identity content as markdown string
    """
    identity_path = AGENTS_DIR / agent_id / "identity.md"
    if identity_path.exists():
        return identity_path.read_text()

    # Create from template if available
    template_path = AGENTS_DIR / agent_id / "identity.template.md"
    if template_path.exists():
        identity_content = template_path.read_text()
        identity_path.write_text(identity_content)
        return identity_content

    # Default identity
    name = config.get("name", agent_id) if config else agent_id
    return f"You are {name}, a helpful assistant."


def get_user_identity(agent_id: str) -> str:
    """Load the user's identity for context.

    All agents serve the user, so they need to know who the user is.
    This returns the user's identity.md content, which contains their
    purpose, values, interests, biographical info, etc.

    Args:
        agent_id: The calling agent's ID (to check if it's the user agent)

    Returns:
        User identity content
    """
    # Don't include user identity for the user agent itself
    if agent_id == "user":
        return "(You are the user.)"

    user_identity_path = AGENTS_DIR / "user" / "identity.md"
    if user_identity_path.exists():
        return user_identity_path.read_text()
    return "(User identity not yet established. Learn about them through conversation.)"


def save_identity(agent_id: str, content: str) -> None:
    """Save agent identity to disk.

    Args:
        agent_id: The agent's ID
        content: Identity content as markdown string
    """
    identity_path = AGENTS_DIR / agent_id / "identity.md"
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity_path.write_text(content)


def get_identity_path(agent_id: str) -> Path:
    """Get the path to an agent's identity file.

    Args:
        agent_id: The agent's ID

    Returns:
        Path to identity.md
    """
    return AGENTS_DIR / agent_id / "identity.md"


class IdentityManager:
    """Manages identity loading and saving for an agent.

    Provides a class-based interface for identity operations.
    """

    def __init__(self, agent_id: str):
        """Initialize identity manager for an agent.

        Args:
            agent_id: The agent's ID
        """
        self.agent_id = agent_id
        self._config: Optional[dict] = None
        self._identity: Optional[str] = None

    @property
    def config(self) -> dict:
        """Get agent configuration (lazy loaded)."""
        if self._config is None:
            self._config = load_config(self.agent_id)
        return self._config

    @property
    def identity(self) -> str:
        """Get agent identity (lazy loaded)."""
        if self._identity is None:
            self._identity = load_identity(self.agent_id, self.config)
        return self._identity

    def reload(self) -> None:
        """Reload config and identity from disk."""
        self._config = None
        self._identity = None

    def get_user_identity(self) -> str:
        """Get the user's identity for context."""
        return get_user_identity(self.agent_id)

    def save(self, content: str) -> None:
        """Save identity to disk."""
        save_identity(self.agent_id, content)
        self._identity = content
