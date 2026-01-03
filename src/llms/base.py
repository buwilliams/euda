"""
LLM Base Classes and Configuration

Provides abstract base class, unified response types, and provider factory.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict


DATA_DIR = Path(__file__).parent.parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"

# Valid provider IDs (must have corresponding provider class)
VALID_PROVIDERS = {"anthropic", "openai", "grok"}


# ============== Unified Response Classes ==============

@dataclass
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class TextBlock:
    type: str = "text"
    text: str = ""


@dataclass
class ToolUseBlock:
    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict = None


@dataclass
class UnifiedResponse:
    """Unified response format across providers."""
    content: list  # List of TextBlock or ToolUseBlock
    stop_reason: str  # "end_turn", "tool_use", etc.
    usage: Usage


# ============== Abstract Provider ==============

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def create_message(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: list,
        tools: Optional[list] = None
    ) -> UnifiedResponse:
        """Create a message/completion.

        Args:
            model: Model identifier
            max_tokens: Maximum tokens in response
            system: System prompt
            messages: Conversation messages
            tools: Optional tool definitions (Anthropic format)

        Returns:
            UnifiedResponse with content, stop_reason, and usage
        """
        pass


# ============== Configuration ==============

# Cached configuration
_config_cache: dict = None


class ConfigError(Exception):
    """Raised when config.json is missing or invalid."""
    pass


def _load_config() -> dict:
    """Load and validate system configuration."""
    if not CONFIG_PATH.exists():
        raise ConfigError(f"Config file not found: {CONFIG_PATH}")

    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file: {e}")

    # Validate required structure
    if "llm" not in config:
        raise ConfigError("Config missing 'llm' section")
    if "provider" not in config["llm"]:
        raise ConfigError("Config missing 'llm.provider'")
    if "providers" not in config["llm"]:
        raise ConfigError("Config missing 'llm.providers'")

    provider = config["llm"]["provider"]
    if provider not in VALID_PROVIDERS:
        raise ConfigError(f"Unknown provider '{provider}'. Valid: {VALID_PROVIDERS}")
    if provider not in config["llm"]["providers"]:
        raise ConfigError(f"Provider '{provider}' not configured in llm.providers")

    return config


def _get_cached_config() -> dict:
    """Get cached config, loading from disk if needed."""
    global _config_cache
    if _config_cache is None:
        _config_cache = _load_config()
    return _config_cache


def get_provider() -> str:
    """Get the configured LLM provider."""
    config = _get_cached_config()
    return config["llm"]["provider"]


def get_model() -> str:
    """Get the configured model for the current provider."""
    config = _get_cached_config()
    provider = config["llm"]["provider"]
    return config["llm"]["providers"][provider]["model"]


def get_providers_config() -> Dict[str, dict]:
    """Get full provider configuration for API/UI."""
    config = _get_cached_config()
    providers = config["llm"]["providers"]

    result = {}
    for provider_id, provider_info in providers.items():
        result[provider_id] = {
            "id": provider_id,
            "display_name": provider_info["display_name"],
            "description": provider_info["description"],
            "model": provider_info["model"]
        }
    return result


# ============== Provider Factory ==============

# Cached client instance
_cached_client: "UnifiedClient" = None


def get_client() -> "UnifiedClient":
    """Get a unified LLM client for the configured provider.

    Returns cached client, creating one if cache was invalidated.
    Client stores both provider and model at creation time to avoid race conditions.
    """
    global _cached_client

    if _cached_client is None:
        provider = get_provider()
        model = get_model()
        print(f"[DEBUG] get_client: Creating new client for provider={provider}, model={model}")
        _cached_client = UnifiedClient(provider, model)
    else:
        print(f"[DEBUG] get_client: Using cached client for provider={_cached_client.provider_name}, model={_cached_client.model_name}")

    return _cached_client


def invalidate_client():
    """Invalidate cached client and config. Call when settings change."""
    global _cached_client, _config_cache
    _cached_client = None
    _config_cache = None


class UnifiedClient:
    """Wrapper that delegates to the appropriate provider."""

    def __init__(self, provider: str, model: str):
        self.provider_name = provider
        self.model_name = model
        self._provider = self._create_provider(provider)

    def _create_provider(self, provider: str) -> LLMProvider:
        """Create the appropriate provider instance."""
        print(f"[DEBUG] UnifiedClient._create_provider: Creating {provider} provider")
        if provider == "anthropic":
            from .anthropic import AnthropicProvider
            return AnthropicProvider()
        elif provider == "openai":
            from .openai import OpenAIProvider
            return OpenAIProvider()
        elif provider == "grok":
            from .grok import GrokProvider
            return GrokProvider()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def messages_create(self, model: str, max_tokens: int, system: str,
                        tools: Optional[list], messages: list) -> UnifiedResponse:
        """Create a message with unified interface."""
        return self._provider.create_message(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools
        )

    def create(self, model: str, max_tokens: int, system: str,
               tools: Optional[list] = None, messages: list = None) -> UnifiedResponse:
        """Alias for messages_create for API compatibility."""
        return self.messages_create(model, max_tokens, system, tools, messages)

    @property
    def messages(self):
        """Provide messages.create() interface for compatibility."""
        return self
