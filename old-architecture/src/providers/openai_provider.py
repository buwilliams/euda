"""
OpenAI provider implementation.

Wraps the OpenAI SDK and handles format conversion from Anthropic-style
tool definitions and messages.
"""

import json
from openai import OpenAI
from .base import LLMProvider, LLMResponse, ToolCall


class OpenAIProvider(LLMProvider):
    """OpenAI GPT API provider."""

    def __init__(self):
        # Client reads OPENAI_API_KEY from environment automatically
        self.client = OpenAI()

    def create_message(
        self,
        model: str,
        system: str,
        messages: list[dict],
        tools: list[dict] = None,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Make an API call to OpenAI."""
        # OpenAI uses system message in the messages array
        openai_messages = [{"role": "system", "content": system}]
        openai_messages.extend(self._convert_messages(messages))

        kwargs = {
            "model": model,
            "max_completion_tokens": max_tokens,
            "messages": openai_messages,
        }
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = self.client.chat.completions.create(**kwargs)
        return self._normalize_response(response)

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
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

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """Convert Anthropic-style messages to OpenAI format."""
        converted = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            # Pass through tool messages unchanged (already in OpenAI format)
            if role == "tool":
                converted.append(msg)
                continue

            if role == "user":
                # Check if this is a tool results message
                if isinstance(content, list) and content:
                    first = content[0]
                    if isinstance(first, dict) and first.get("type") == "tool_result":
                        # Convert each tool result to OpenAI format
                        for result in content:
                            converted.append({
                                "role": "tool",
                                "tool_call_id": result.get("tool_use_id"),
                                "content": result.get("content", "")
                            })
                        continue

                # Regular user message
                if isinstance(content, str):
                    converted.append({"role": "user", "content": content})
                else:
                    # Handle complex content (text blocks, etc.)
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            text_parts.append(block["text"])
                        elif hasattr(block, "text"):
                            text_parts.append(block.text)
                    converted.append({"role": "user", "content": "\n".join(text_parts) if text_parts else str(content)})

            elif role == "assistant":
                # Check if already in OpenAI format (has tool_calls key)
                if "tool_calls" in msg:
                    converted.append(msg)
                    continue

                if isinstance(content, str):
                    converted.append({"role": "assistant", "content": content})
                elif isinstance(content, list):
                    # Handle Anthropic content blocks (tool_use and text)
                    tool_calls = []
                    text_content = []

                    for block in content:
                        if hasattr(block, "type"):
                            # Anthropic SDK object
                            if block.type == "tool_use":
                                tool_calls.append({
                                    "id": block.id,
                                    "type": "function",
                                    "function": {
                                        "name": block.name,
                                        "arguments": json.dumps(block.input)
                                    }
                                })
                            elif hasattr(block, "text"):
                                text_content.append(block.text)
                        elif isinstance(block, dict):
                            # Dict format
                            if block.get("type") == "tool_use":
                                tool_calls.append({
                                    "id": block.get("id"),
                                    "type": "function",
                                    "function": {
                                        "name": block.get("name"),
                                        "arguments": json.dumps(block.get("input", {}))
                                    }
                                })
                            elif "text" in block:
                                text_content.append(block["text"])

                    assistant_msg = {"role": "assistant"}
                    if text_content:
                        assistant_msg["content"] = "\n".join(text_content)
                    else:
                        assistant_msg["content"] = None
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls
                    converted.append(assistant_msg)
                else:
                    converted.append({"role": "assistant", "content": str(content)})

        return converted

    def _normalize_response(self, response) -> LLMResponse:
        """Convert OpenAI response to normalized format."""
        message = response.choices[0].message
        tool_calls = []
        text_blocks = []

        if message.content:
            text_blocks.append(message.content)

        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments)
                ))

        return LLMResponse(
            content=message,  # Keep raw for context
            tool_calls=tool_calls,
            text_blocks=text_blocks,
            stop_reason=response.choices[0].finish_reason
        )

    def format_tool_result(
        self,
        tool_call_id: str,
        content: str,
        is_error: bool = False
    ) -> dict:
        """Format tool result for OpenAI."""
        # OpenAI doesn't have a special error flag
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": f"Error: {content}" if is_error else content
        }

    def format_tool_results_message(self, tool_results: list[dict]) -> list[dict]:
        """OpenAI expects each tool result as a separate message."""
        # Return as list - caller handles this
        return tool_results

    def format_assistant_message(self, response: LLMResponse) -> dict:
        """Format assistant response for conversation history."""
        msg = {"role": "assistant"}

        # Handle text content
        if response.text_blocks:
            msg["content"] = "\n".join(response.text_blocks)
        else:
            msg["content"] = None

        # Handle tool calls
        if response.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.input)
                    }
                }
                for tc in response.tool_calls
            ]

        return msg
