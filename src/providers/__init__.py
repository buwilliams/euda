"""
LLM Provider abstraction layer.

Provides a unified interface for different LLM providers with configuration
stored in data/shared/config/llm.json.

Usage:
    from src.providers import get_provider, get_model_for_agent, load_config

    # Get default provider
    provider = get_provider()

    # Get specific provider
    provider = get_provider("openai")

    # Get provider and model for an agent (respects agent_overrides)
    provider_name, model = get_model_for_agent("ingestion")
    provider = get_provider(provider_name)
"""

import json
from pathlib import Path
from typing import Optional

from .base import LLMProvider, LLMResponse, ToolCall

# Config location
CONFIG_DIR = Path(__file__).parent.parent.parent / "data" / "shared" / "config"
CONFIG_FILE = CONFIG_DIR / "llm.json"

# Default configuration
DEFAULT_CONFIG = {
    "default_provider": "anthropic",
    "providers": {
        "anthropic": {
            "enabled": True,
            "default_model": "claude-sonnet-4-20250514",
            "max_tokens": 8096
        },
        "openai": {
            "enabled": True,
            "default_model": "gpt-4o",
            "max_tokens": 4096
        }
    },
    "agent_overrides": {}
}

# Module-level cache
_config: Optional[dict] = None
_providers: dict[str, LLMProvider] = {}


def load_config() -> dict:
    """
    Load LLM configuration from file.

    Creates default config if file doesn't exist.
    """
    global _config

    if _config is not None:
        return _config

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            _config = json.load(f)
    else:
        _config = DEFAULT_CONFIG.copy()
        # Create config directory and file with defaults
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(_config, f, indent=2)

    return _config


def reload_config():
    """Force reload of configuration (useful for runtime changes)."""
    global _config, _providers
    _config = None
    _providers = {}
    load_config()


def get_provider(name: Optional[str] = None) -> LLMProvider:
    """
    Get a provider instance by name.

    Args:
        name: Provider name ("anthropic" or "openai"). If None, uses default.

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider is unknown or not enabled
    """
    config = load_config()

    if name is None:
        name = config.get("default_provider", "anthropic")

    # Check if provider is enabled
    provider_config = config.get("providers", {}).get(name, {})
    if not provider_config.get("enabled", True):
        raise ValueError(f"Provider '{name}' is not enabled")

    # Create provider instance if not cached
    if name not in _providers:
        if name == "anthropic":
            from .anthropic_provider import AnthropicProvider
            _providers[name] = AnthropicProvider()
        elif name == "openai":
            from .openai_provider import OpenAIProvider
            _providers[name] = OpenAIProvider()
        else:
            raise ValueError(f"Unknown provider: {name}")

    return _providers[name]


def get_provider_config(name: Optional[str] = None) -> dict:
    """
    Get configuration for a specific provider.

    Args:
        name: Provider name. If None, uses default.

    Returns:
        Provider configuration dict
    """
    config = load_config()

    if name is None:
        name = config.get("default_provider", "anthropic")

    return config.get("providers", {}).get(name, {})


def get_model_for_agent(agent_name: str) -> tuple[str, str]:
    """
    Get provider and model for a specific agent.

    Checks agent_overrides first, then falls back to defaults.

    Args:
        agent_name: Name of the agent (e.g., "ingestion", "summary")

    Returns:
        Tuple of (provider_name, model_name)
    """
    config = load_config()

    # Check for agent-specific override
    overrides = config.get("agent_overrides", {})
    if agent_name in overrides:
        override = overrides[agent_name]
        provider_name = override.get("provider", config["default_provider"])
        model = override.get("model")
        if model is None:
            model = config["providers"][provider_name]["default_model"]
        return provider_name, model

    # Use defaults
    provider_name = config["default_provider"]
    model = config["providers"][provider_name]["default_model"]
    return provider_name, model


# Export public API
__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ToolCall",
    "load_config",
    "reload_config",
    "get_provider",
    "get_provider_config",
    "get_model_for_agent",
]
