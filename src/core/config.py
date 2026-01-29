"""
Configuration utilities for layered config loading.

Supports a defaults + overrides pattern:
- config.defaults.json: Base config tracked in git
- config.json: User overrides (gitignored)

The two are deep-merged at load time, with user config taking precedence.
"""

import json
from pathlib import Path
from typing import Any, Optional


def deep_merge(base: dict, overrides: dict) -> dict:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary (defaults)
        overrides: Override dictionary (user config)

    Returns:
        Merged dictionary with overrides taking precedence.
        For nested dicts, merges recursively.
        For arrays and other types, overrides replace entirely.
    """
    result = base.copy()

    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = deep_merge(result[key], value)
        else:
            # Override (including arrays - user specifies full list)
            result[key] = value

    return result


def load_layered_config(
    config_dir: Path,
    defaults_filename: str = "config.defaults.json",
    overrides_filename: str = "config.json"
) -> Optional[dict]:
    """Load config with defaults + overrides pattern.

    Args:
        config_dir: Directory containing config files
        defaults_filename: Name of defaults file (tracked in git)
        overrides_filename: Name of overrides file (gitignored)

    Returns:
        Merged config dict, or None if no config files exist.
        If only defaults exist, returns defaults.
        If only overrides exist, returns overrides.
        If both exist, deep merges with overrides taking precedence.
    """
    defaults_path = config_dir / defaults_filename
    overrides_path = config_dir / overrides_filename

    defaults = {}
    overrides = {}

    # Load defaults if exists
    if defaults_path.exists():
        with open(defaults_path) as f:
            defaults = json.load(f)

    # Load overrides if exists
    if overrides_path.exists():
        with open(overrides_path) as f:
            overrides = json.load(f)

    # Return merged result
    if defaults or overrides:
        return deep_merge(defaults, overrides)

    return None


def save_config_overrides(
    config_dir: Path,
    overrides: dict,
    overrides_filename: str = "config.json"
) -> None:
    """Save user config overrides.

    Args:
        config_dir: Directory to save to
        overrides: Override config to save
        overrides_filename: Name of overrides file
    """
    overrides_path = config_dir / overrides_filename
    with open(overrides_path, "w") as f:
        json.dump(overrides, f, indent=2)
        f.write("\n")
