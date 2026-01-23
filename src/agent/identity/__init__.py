"""
Identity Module - Agent identity loading and management.

Identity is the "who am I?" aspect of an agent.
"""

from .identity import (
    load_config,
    load_identity,
    get_user_identity,
    save_identity,
    get_identity_path,
    IdentityManager,
    AGENTS_DIR,
)

__all__ = [
    "load_config",
    "load_identity",
    "get_user_identity",
    "save_identity",
    "get_identity_path",
    "IdentityManager",
    "AGENTS_DIR",
]
