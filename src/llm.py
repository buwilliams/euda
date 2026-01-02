"""
LLM Configuration

Centralized configuration for AI providers and models.
Reads from data/system/config.json, falls back to defaults.
"""

import json
from pathlib import Path

import anthropic


DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"

# Defaults
DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _load_config() -> dict:
    """Load system configuration."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def get_provider() -> str:
    """Get the configured LLM provider."""
    config = _load_config()
    return config.get("llm", {}).get("provider", DEFAULT_PROVIDER)


def get_model() -> str:
    """Get the configured model for the current provider."""
    config = _load_config()
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", DEFAULT_PROVIDER)
    return llm_config.get("models", {}).get(provider, DEFAULT_MODEL)


def get_client():
    """Get an LLM client for the configured provider."""
    provider = get_provider()

    if provider == "anthropic":
        return anthropic.Anthropic()
    else:
        # Default to Anthropic
        return anthropic.Anthropic()
