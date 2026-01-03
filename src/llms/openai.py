"""
OpenAI Provider - GPT models

Converts between Anthropic's tool/message format and OpenAI's format.
"""

import json
from typing import Optional

import openai

from .base import LLMProvider, UnifiedResponse, Usage, TextBlock, ToolUseBlock


class OpenAIProvider(LLMProvider):
    """OpenAI/GPT provider implementation."""

    def __init__(self):
        self.client = openai.OpenAI()

    def create_message(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: list,
        tools: Optional[list] = None
    ) -> UnifiedResponse:
        """Create a message using OpenAI's API.

        Converts Anthropic format to OpenAI format, calls API, converts back.
        """
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(system, messages)

        # Convert tools to OpenAI format
        openai_tools = self._convert_tools(tools) if tools else None

        # Make API call
        kwargs = {
            "model": model,
            "max_completion_tokens": max_tokens,
            "messages": openai_messages,
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = self.client.chat.completions.create(**kwargs)

        # Convert response to unified format
        return self._parse_response(response)

    def _convert_messages(self, system: str, messages: list) -> list:
        """Convert Anthropic message format to OpenAI format."""
        openai_messages = [{"role": "system", "content": system}]

        for msg in messages:
            if msg["role"] == "user":
                # Handle tool results
                if isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if item.get("type") == "tool_result":
                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": item["tool_use_id"],
                                "content": item["content"]
                            })
                else:
                    openai_messages.append({"role": "user", "content": msg["content"]})

            elif msg["role"] == "assistant":
                # Handle assistant messages with tool calls
                if isinstance(msg["content"], list):
                    tool_calls = []
                    text_content = ""
                    for block in msg["content"]:
                        if hasattr(block, "type") and block.type == "tool_use":
                            tool_calls.append({
                                "id": block.id,
                                "type": "function",
                                "function": {
                                    "name": block.name,
                                    "arguments": json.dumps(block.input)
                                }
                            })
                        elif hasattr(block, "text"):
                            text_content += block.text
                    assistant_msg = {"role": "assistant", "content": text_content or None}
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls
                    openai_messages.append(assistant_msg)
                else:
                    openai_messages.append({"role": "assistant", "content": msg["content"]})

        return openai_messages

    def _convert_tools(self, tools: list) -> list:
        """Convert Anthropic tool format to OpenAI function format."""
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}})
                }
            })
        return openai_tools

    def _parse_response(self, response) -> UnifiedResponse:
        """Convert OpenAI response to unified format."""
        choice = response.choices[0]
        message = choice.message
        content = []

        # Handle text content
        if message.content:
            content.append(TextBlock(text=message.content))

        # Handle tool calls
        if message.tool_calls:
            for tool_call in message.tool_calls:
                content.append(ToolUseBlock(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    input=json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                ))

        # Map finish reason
        stop_reason = "end_turn"
        if choice.finish_reason == "tool_calls":
            stop_reason = "tool_use"
        elif choice.finish_reason == "stop":
            stop_reason = "end_turn"

        return UnifiedResponse(
            content=content,
            stop_reason=stop_reason,
            usage=Usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
        )
