"""
Claude Provider - Anthropic's Claude models

Uses the native Anthropic SDK. Response format is used as the canonical
format that other providers convert to.
"""

from typing import Optional

import anthropic

from .base import LLMProvider, UnifiedResponse, Usage


class ClaudeProvider(LLMProvider):
    """Claude provider implementation using Anthropic SDK."""

    def __init__(self):
        self.client = anthropic.Anthropic()

    def create_message(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: list,
        tools: Optional[list] = None
    ) -> UnifiedResponse:
        """Create a message using Anthropic's API.

        Anthropic's response format is used as-is since it's our canonical format.
        """
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        # Extract cached tokens (Anthropic tracks cache_read and cache_creation separately)
        cached_tokens = getattr(response.usage, 'cache_read_input_tokens', 0) or 0

        # Return with proper Usage object that includes cached tokens
        return UnifiedResponse(
            content=response.content,
            stop_reason=response.stop_reason,
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cached_input_tokens=cached_tokens
            )
        )
