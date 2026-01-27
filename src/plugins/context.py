"""
Plugin Context - Build environment variables for plugin execution.

Plugins receive context through environment variables, keeping them decoupled
from the Euno internals while still having access to necessary information.
"""

import os
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent.parent / "data"


def build_plugin_env(
    agent_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> dict:
    """Build environment variables for plugin execution.

    Args:
        agent_id: Current agent ID (if agent context exists)
        topic_id: Current topic being worked (if in work cycle)
        session_id: Chat session ID (during chat)

    Returns:
        Dict of environment variables to pass to subprocess
    """
    # Start with current environment
    env = os.environ.copy()

    # Add Euno-specific variables
    env["EUNO_DATA_DIR"] = str(DATA_DIR.resolve())

    if agent_id:
        env["EUNO_AGENT_ID"] = agent_id

    if topic_id:
        env["EUNO_TOPIC_ID"] = topic_id

    if session_id:
        env["EUNO_SESSION_ID"] = session_id

    return env


def get_data_dir_from_env() -> Path:
    """Get the data directory from environment (for use inside plugins).

    Returns:
        Path to data directory, either from EUNO_DATA_DIR env var
        or the default location.
    """
    env_dir = os.environ.get("EUNO_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return DATA_DIR


def get_agent_id_from_env() -> Optional[str]:
    """Get the agent ID from environment (for use inside plugins)."""
    return os.environ.get("EUNO_AGENT_ID")


def get_topic_id_from_env() -> Optional[str]:
    """Get the topic ID from environment (for use inside plugins)."""
    return os.environ.get("EUNO_TOPIC_ID")


def get_session_id_from_env() -> Optional[str]:
    """Get the session ID from environment (for use inside plugins)."""
    return os.environ.get("EUNO_SESSION_ID")
