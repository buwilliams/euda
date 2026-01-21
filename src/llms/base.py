"""
LLM Base Classes and Configuration

Provides abstract base class, unified response types, and provider factory.
All LLM calls go through UnifiedClient which handles:
- Budget checking (before call)
- Cost tracking (after call)
- Rate limiting with exponential backoff
- Prompt logging
"""

import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict

from ..logger import get_logger


DATA_DIR = Path(__file__).parent.parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"

# Prompt logger instance (lazy loaded)
_prompt_logger = None


def _get_prompt_logger():
    """Get the prompt logger instance."""
    global _prompt_logger
    if _prompt_logger is None:
        _prompt_logger = get_logger("system/logs/prompts")
    return _prompt_logger


def _log_prompt(agent_id: str, model: str, system: str, messages: list, tools: list = None,
                timestamp: str = None, response: "UnifiedResponse" = None):
    """Log the full prompt and response to the API."""
    entry = {
        "timestamp": timestamp or datetime.now().isoformat(),
        "agent": agent_id,
        "model": model,
        "system_prompt": system,
        "system_prompt_length": len(system),
        "messages": messages,
        "tools": [t.get("name") for t in tools] if tools else None,
    }

    # Add response if available
    if response:
        response_content = []
        for block in response.content:
            if hasattr(block, 'text'):
                response_content.append({"type": "text", "text": block.text})
            elif hasattr(block, 'name'):
                response_content.append({
                    "type": "tool_use",
                    "name": block.name,
                    "input": block.input
                })
        entry["response"] = {
            "content": response_content,
            "stop_reason": response.stop_reason
        }

    _get_prompt_logger().write_raw(entry)

# Valid provider IDs (must have corresponding provider class)
VALID_PROVIDERS = {"anthropic", "openai", "grok"}


# ============== Unified Response Classes ==============

@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0


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
        _cached_client = UnifiedClient(provider, model)

    return _cached_client


def invalidate_client():
    """Invalidate cached client and config. Call when settings change."""
    global _cached_client, _config_cache
    _cached_client = None
    _config_cache = None


class UnifiedClient:
    """Wrapper that delegates to the appropriate provider.

    Handles all cross-cutting concerns automatically:
    - Budget checking (before each call)
    - Cost tracking (after each call)
    - Rate limiting with exponential backoff
    - Prompt logging
    """

    def __init__(self, provider: str, model: str):
        self.provider_name = provider
        self.model_name = model
        self._provider = self._create_provider(provider)

        # Rate limiting state
        self._backoff_until: Optional[float] = None
        self._consecutive_rate_limits: int = 0

    def _create_provider(self, provider: str) -> LLMProvider:
        """Create the appropriate provider instance."""
        if provider == "anthropic":
            from .claude import ClaudeProvider
            return ClaudeProvider()
        elif provider == "openai":
            from .chatgpt import ChatGPTProvider
            return ChatGPTProvider()
        elif provider == "grok":
            try:
                from .grok import GrokProvider
                return GrokProvider()
            except ImportError:
                raise ImportError(
                    "Grok provider requires xai-sdk. Install with: pip install xai-sdk"
                )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _wait_for_backoff(self):
        """Block until backoff period ends."""
        if self._backoff_until and time.time() < self._backoff_until:
            wait_time = self._backoff_until - time.time()
            print(f"[LLM] Rate limited, waiting {wait_time:.1f}s...")
            time.sleep(wait_time)

    def _handle_rate_limit(self):
        """Calculate and set backoff after a rate limit."""
        self._consecutive_rate_limits += 1
        # Exponential backoff: 2, 4, 8, 16... up to 240 seconds (4 min)
        backoff_seconds = min(2 ** self._consecutive_rate_limits, 240)
        self._backoff_until = time.time() + backoff_seconds
        print(f"[LLM] Rate limit hit, backing off {backoff_seconds}s (attempt {self._consecutive_rate_limits})")

    def _reset_backoff(self):
        """Reset backoff state after successful call."""
        self._consecutive_rate_limits = 0
        self._backoff_until = None

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception is a rate limit error."""
        error_str = str(error).lower()
        return any(phrase in error_str for phrase in [
            "429", "rate_limit", "rate limit", "too many requests",
            "insufficient_quota", "quota exceeded", "quota"
        ])

    def create(
        self,
        max_tokens: int,
        system: str,
        messages: list,
        tools: Optional[list] = None,
        agent_id: str = "unknown",
        job_id: Optional[str] = None,
        track_cost: bool = True,
        enabled_agent_count: int = 1,
    ) -> UnifiedResponse:
        """Create a message with automatic cost tracking and rate limiting.

        Args:
            max_tokens: Maximum tokens in response
            system: System prompt
            messages: Conversation messages
            tools: Optional tool definitions
            agent_id: ID of calling agent (required for cost attribution)
            job_id: ID of job being worked on (for per-job tracking)
            track_cost: Whether to track costs (default True)
            enabled_agent_count: Number of enabled agents for budget splitting

        Returns:
            UnifiedResponse with content, stop_reason, and usage

        Raises:
            BudgetExceeded: If budget limit reached
            AgentPausedError: If agent is paused due to threshold breach
            RateLimitExceeded: If rate limit exceeded
        """
        from ..agent.cognition.metacognition import (
            get_token_awareness, estimate_request_tokens
        )

        token_awareness = get_token_awareness()

        # 1. Pre-call: estimate input tokens
        estimated_input = estimate_request_tokens(system, messages, tools)

        # 2. Pre-call: check token awareness thresholds (may raise AgentPausedError)
        token_awareness.acquire(agent_id, estimated_input, enabled_agent_count)

        # 5. Pre-call: wait for any active backoff
        self._wait_for_backoff()

        # 6. Generate timestamp for correlation between prompt and cost logs
        call_timestamp = datetime.now().isoformat()

        # 7. Make the call with timing
        start_time = time.time()
        try:
            response = self._provider.create_message(
                model=self.model_name,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=tools
            )
        except Exception as e:
            if self._is_rate_limit_error(e):
                self._handle_rate_limit()
            raise

        duration_ms = int((time.time() - start_time) * 1000)

        # 8. Post-call: reset backoff on success
        self._reset_backoff()

        # 9. Post-call: record token usage
        token_awareness.record(
            agent_id=agent_id,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            provider=self.provider_name,
            model=self.model_name,
            enabled_agent_count=enabled_agent_count,
            job_id=job_id,
            cached_input_tokens=response.usage.cached_input_tokens,
            stop_reason=response.stop_reason,
            duration_ms=duration_ms,
            timestamp=call_timestamp
        )

        # 10. Post-call: log prompt and response together
        _log_prompt(agent_id, self.model_name, system, messages, tools,
                    timestamp=call_timestamp, response=response)

        return response
