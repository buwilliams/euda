"""
Grok Provider - xAI's Grok models

Uses the official xai-sdk Python library.
"""

import json
from typing import Optional

from xai_sdk import Client
from xai_sdk.chat import user, system as system_msg, assistant, tool, tool_result

from .base import LLMProvider, UnifiedResponse, Usage, TextBlock, ToolUseBlock


class GrokProvider(LLMProvider):
    """xAI/Grok provider implementation using native xai-sdk."""

    def __init__(self):
        # Uses XAI_API_KEY environment variable automatically
        self.client = Client()

    def create_message(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: list,
        tools: Optional[list] = None
    ) -> UnifiedResponse:
        """Create a message using xAI's native SDK."""
        # Convert messages to xai-sdk format
        xai_messages = self._convert_messages(system, messages)

        # Convert tools to xai-sdk format
        xai_tools = self._convert_tools(tools) if tools else None

        # Create chat and sample
        kwargs = {
            "model": model,
            "messages": xai_messages,
            "max_tokens": max_tokens,
        }
        if xai_tools:
            kwargs["tools"] = xai_tools

        chat = self.client.chat.create(**kwargs)
        response = chat.sample()

        return self._parse_response(response)

    def _convert_messages(self, system_prompt: str, messages: list) -> list:
        """Convert Anthropic message format to xai-sdk format."""
        xai_messages = [system_msg(system_prompt)]

        for msg in messages:
            if msg["role"] == "user":
                # Handle tool results
                if isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if item.get("type") == "tool_result":
                            xai_messages.append(tool_result(
                                tool_call_id=item["tool_use_id"],
                                result=item["content"]
                            ))
                        elif item.get("type") == "text":
                            xai_messages.append(user(item["text"]))
                else:
                    xai_messages.append(user(msg["content"]))

            elif msg["role"] == "assistant":
                # Handle assistant messages with tool calls
                if isinstance(msg["content"], list):
                    text_content = ""
                    for block in msg["content"]:
                        if hasattr(block, "type") and block.type == "text":
                            text_content += block.text
                        elif hasattr(block, "text"):
                            text_content += block.text
                    if text_content:
                        xai_messages.append(assistant(text_content))
                else:
                    xai_messages.append(assistant(msg["content"]))

        return xai_messages

    def _convert_tools(self, tools: list) -> list:
        """Convert Anthropic tool format to xai-sdk format."""
        xai_tools = []
        for t in tools:
            xai_tools.append(tool(
                name=t["name"],
                description=t.get("description", ""),
                parameters=t.get("input_schema", {"type": "object", "properties": {}})
            ))
        return xai_tools

    def _parse_response(self, response) -> UnifiedResponse:
        """Convert xai-sdk response to unified format."""
        content = []

        # Handle text content
        if response.content:
            content.append(TextBlock(text=response.content))

        # Handle tool calls
        if response.tool_calls:
            for tc in response.tool_calls:
                content.append(ToolUseBlock(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments) if tc.function.arguments else {}
                ))

        # Map finish reason
        stop_reason = "end_turn"
        if response.finish_reason == "FINISH_REASON_TOOL_CALLS":
            stop_reason = "tool_use"
        elif response.finish_reason in ("FINISH_REASON_STOP", "FINISH_REASON_EOS_TOKEN"):
            stop_reason = "end_turn"

        return UnifiedResponse(
            content=content,
            stop_reason=stop_reason,
            usage=Usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
        )
