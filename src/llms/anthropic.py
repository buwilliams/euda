"""
Anthropic Provider - Claude models

Uses the native Anthropic SDK. Response format is used as the canonical
format that other providers convert to.
"""

from typing import Optional

import anthropic

from .base import LLMProvider, UnifiedResponse


class AnthropicProvider(LLMProvider):
    """Anthropic/Claude provider implementation."""

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

        # Anthropic's response already matches our UnifiedResponse format
        return self.client.messages.create(**kwargs)
