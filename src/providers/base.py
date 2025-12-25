"""
Base classes for LLM provider abstraction.

Provides a unified interface for different LLM providers (Anthropic, OpenAI, etc.)
so agents can work with any configured provider without code changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolCall:
    """Normalized tool call representation."""
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    """Normalized response from any LLM provider."""
    content: Any  # Raw content for context storage
    tool_calls: list[ToolCall] = field(default_factory=list)
    text_blocks: list[str] = field(default_factory=list)
    stop_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def create_message(
        self,
        model: str,
        system: str,
        messages: list[dict],
        tools: list[dict] = None,
        max_tokens: int = 8096
    ) -> LLMResponse:
        """
        Make an API call and return a normalized response.

        Args:
            model: Model identifier (e.g., "claude-sonnet-4-20250514", "gpt-4o")
            system: System prompt
            messages: Conversation history
            tools: Tool definitions (in Anthropic format with input_schema)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with normalized tool_calls, text_blocks, and raw content
        """
        pass

    @abstractmethod
    def format_tool_result(
        self,
        tool_call_id: str,
        content: str,
        is_error: bool = False
    ) -> dict:
        """
        Format a tool result for the provider's expected format.

        Args:
            tool_call_id: ID of the tool call being responded to
            content: Result content (stringified)
            is_error: Whether this is an error result

        Returns:
            Provider-specific tool result dict
        """
        pass

    @abstractmethod
    def format_tool_results_message(self, tool_results: list[dict]) -> dict:
        """
        Format tool results into a message for the conversation.

        Args:
            tool_results: List of formatted tool results

        Returns:
            Message dict to append to conversation
        """
        pass

    @abstractmethod
    def format_assistant_message(self, response: LLMResponse) -> dict:
        """
        Format an assistant response for conversation history.

        Args:
            response: The LLM response

        Returns:
            Message dict to append to conversation
        """
        pass
