"""
Anthropic provider implementation.

Wraps the Anthropic SDK to provide a unified interface.
"""

from anthropic import Anthropic
from .base import LLMProvider, LLMResponse, ToolCall


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self):
        # Client reads ANTHROPIC_API_KEY from environment automatically
        self.client = Anthropic()

    def create_message(
        self,
        model: str,
        system: str,
        messages: list[dict],
        tools: list[dict] = None,
        max_tokens: int = 8096
    ) -> LLMResponse:
        """Make an API call to Anthropic."""
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            # Tools are already in Anthropic format (with input_schema)
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)
        return self._normalize_response(response)

    def _normalize_response(self, response) -> LLMResponse:
        """Convert Anthropic response to normalized format."""
        tool_calls = []
        text_blocks = []

        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input
                ))
            elif hasattr(block, 'text'):
                text_blocks.append(block.text)

        return LLMResponse(
            content=response.content,  # Keep raw for context
            tool_calls=tool_calls,
            text_blocks=text_blocks,
            stop_reason=response.stop_reason
        )

    def format_tool_result(
        self,
        tool_call_id: str,
        content: str,
        is_error: bool = False
    ) -> dict:
        """Format tool result for Anthropic."""
        result = {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": content
        }
        if is_error:
            result["is_error"] = True
        return result

    def format_tool_results_message(self, tool_results: list[dict]) -> dict:
        """Anthropic expects tool results in a user message."""
        return {
            "role": "user",
            "content": tool_results
        }

    def format_assistant_message(self, response: LLMResponse) -> dict:
        """Format assistant response for conversation history."""
        return {
            "role": "assistant",
            "content": response.content
        }
