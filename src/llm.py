"""
LLM Configuration

Centralized configuration for AI providers and models.
Reads from data/system/config.json, falls back to defaults.

Provides a unified interface across providers (Anthropic, OpenAI).
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import anthropic
import openai


DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"

# Defaults
DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-5.2"


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
    return llm_config.get("models", {}).get(provider, DEFAULT_MODEL)


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


# ============== Unified Client Wrapper ==============

class UnifiedClient:
    """Wrapper providing consistent interface across LLM providers."""

    def __init__(self, provider: str):
        self.provider = provider
        if provider == "openai":
            self.client = openai.OpenAI()
        else:
            self.client = anthropic.Anthropic()

    def _convert_tools_to_openai(self, tools: list) -> list:
        """Convert Anthropic tool format to OpenAI function format."""
        if not tools:
            return None
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

    def _parse_openai_response(self, response) -> UnifiedResponse:
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

    def messages_create(self, model: str, max_tokens: int, system: str,
                        tools: Optional[list], messages: list,
                        agent_id: str = None) -> UnifiedResponse:
        """Create a message with unified interface.

        Args:
            model: Model name to use
            max_tokens: Maximum tokens in response
            system: System prompt
            tools: List of tool definitions (optional)
            messages: Conversation messages
            agent_id: ID of the calling agent for logging (optional)
        """
        from .cost_tracker import check_budget, record_usage

        # Check budget before making API call
        check_budget()

        start_time = time.time()

        if self.provider == "openai":
            # Build OpenAI messages with system prompt
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

            response = self.client.chat.completions.create(
                model=model,
                max_completion_tokens=max_tokens,
                messages=openai_messages,
                tools=self._convert_tools_to_openai(tools) if tools else None
            )
            parsed = self._parse_openai_response(response)
            duration_ms = int((time.time() - start_time) * 1000)

            # Record usage for cost tracking and logging
            record_usage(
                model=model,
                input_tokens=parsed.usage.input_tokens,
                output_tokens=parsed.usage.output_tokens,
                agent_id=agent_id,
                stop_reason=parsed.stop_reason,
                duration_ms=duration_ms
            )

            return parsed
        else:
            # Anthropic - use native client
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages
            }
            if tools:
                kwargs["tools"] = tools
            response = self.client.messages.create(**kwargs)
            duration_ms = int((time.time() - start_time) * 1000)

            # Record usage for cost tracking and logging
            record_usage(
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                agent_id=agent_id,
                stop_reason=response.stop_reason,
                duration_ms=duration_ms
            )

            return response

    def create(self, model: str, max_tokens: int, system: str,
                tools: Optional[list] = None, messages: list = None,
                agent_id: str = None) -> UnifiedResponse:
        """Alias for messages_create for API compatibility."""
        return self.messages_create(model, max_tokens, system, tools, messages, agent_id)

    @property
    def messages(self):
        """Provide messages.create() interface for compatibility."""
        return self


def get_client() -> UnifiedClient:
    """Get a unified LLM client for the configured provider."""
    return UnifiedClient(get_provider())
