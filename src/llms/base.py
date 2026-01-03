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


# ============== Provider Registry ==============

# Provider metadata: display_name, default_model, description
PROVIDERS: Dict[str, dict] = {
    "anthropic": {
        "id": "anthropic",
        "display_name": "Claude",
        "default_model": "claude-opus-4-5",
        "description": "Anthropic's Claude models"
    },
    "openai": {
        "id": "openai",
        "display_name": "GPT",
        "default_model": "gpt-5.2",
        "description": "OpenAI's GPT models"
    },
    "grok": {
        "id": "grok",
        "display_name": "Grok",
        "default_model": "grok-4.1-fast",
        "description": "xAI's Grok models"
    }
}

DEFAULT_PROVIDER = "openai"


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
    # First check config, then fall back to provider default
    config_model = llm_config.get("models", {}).get(provider)
    if config_model:
        return config_model
    return PROVIDERS.get(provider, {}).get("default_model", "")


def get_providers_config() -> Dict[str, dict]:
    """Get full provider configuration for API/UI.

    Returns provider metadata merged with any user-configured models.
    """
    config = _load_config()
    user_models = config.get("llm", {}).get("models", {})

    result = {}
    for provider_id, provider_info in PROVIDERS.items():
        result[provider_id] = {
            "id": provider_id,
            "display_name": provider_info["display_name"],
            "description": provider_info["description"],
            "default_model": user_models.get(provider_id, provider_info["default_model"])
        }
    return result


# ============== Provider Factory ==============

def get_client() -> "UnifiedClient":
    """Get a unified LLM client for the configured provider."""
    return UnifiedClient(get_provider())


class UnifiedClient:
    """Wrapper that delegates to the appropriate provider."""

    def __init__(self, provider: str):
        self.provider_name = provider
        self._provider = self._create_provider(provider)

    def _create_provider(self, provider: str) -> LLMProvider:
        """Create the appropriate provider instance."""
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
