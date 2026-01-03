"""
LLM Configuration and Provider Factory

Centralized configuration for AI providers and models.
Reads from data/system/config.json, falls back to defaults.

Supported providers: anthropic, openai, grok
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List


DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"

# Defaults
DEFAULT_PROVIDER = "openai"
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-5.2",
    "grok": "grok-3"
}


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
    return llm_config.get("models", {}).get(provider, DEFAULT_MODELS.get(provider))


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
            from .llm_anthropic import AnthropicProvider
            return AnthropicProvider()
        elif provider == "openai":
            from .llm_openai import OpenAIProvider
            return OpenAIProvider()
        elif provider == "grok":
            from .llm_grok import GrokProvider
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
