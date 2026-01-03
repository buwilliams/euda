"""
Grok Provider - xAI's Grok models

xAI's API is OpenAI-compatible, so we extend the OpenAI provider
and just change the base URL and API key.
"""

import json
import os
from typing import Optional

import openai

from .base import LLMProvider, UnifiedResponse, Usage, TextBlock, ToolUseBlock
from .openai import OpenAIProvider


class GrokProvider(OpenAIProvider):
    """xAI/Grok provider implementation.

    Extends OpenAI provider since xAI uses an OpenAI-compatible API.
    Uses max_tokens instead of max_completion_tokens for xAI compatibility.
    """

    XAI_BASE_URL = "https://api.x.ai/v1"

    def __init__(self):
        # Use XAI_API_KEY env var, pointing to xAI's API endpoint
        self.client = openai.OpenAI(
            api_key=os.environ.get("XAI_API_KEY"),
            base_url=self.XAI_BASE_URL
        )

    def create_message(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: list,
        tools: Optional[list] = None
    ) -> UnifiedResponse:
        """Create a message using xAI's API.

        Uses max_tokens instead of max_completion_tokens for xAI compatibility.
        """
        openai_messages = self._convert_messages(system, messages)
        openai_tools = self._convert_tools(tools) if tools else None

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,  # xAI uses max_tokens, not max_completion_tokens
            "messages": openai_messages,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = self.client.chat.completions.create(**kwargs)
        return self._parse_response(response)
