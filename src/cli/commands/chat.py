"""
Chat command - Single LLM turn without work cycle.
"""

import json
import sys
from pathlib import Path
from typing import List

from ..formatters import print_header, print_error
from ..stream import SyncEventStream


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_chat(args: List[str], json_mode: bool = False):
    """Single LLM turn without work cycle wrapper.

    Usage:
      dev chat <agent> <message>
      dev chat <agent> <message> --no-tools    Disable tool execution
      dev chat <agent> <message> --no-reflect  Skip reflection append
    """
    # Parse flags
    no_tools = "--no-tools" in args
    no_reflect = "--no-reflect" in args

    clean_args = [a for a in args if a not in ("--no-tools", "--no-reflect")]

    if len(clean_args) < 2:
        print_error("Usage: dev chat <agent> <message> [--no-tools] [--no-reflect]", json_mode)
        sys.exit(1)

    agent_id = clean_args[0]
    message = " ".join(clean_args[1:])

    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    # Create stream for events
    stream = SyncEventStream(json_mode)

    if no_tools:
        # Create a modified agent without tools
        _chat_no_tools(agent_id, message, no_reflect, stream, json_mode)
    else:
        _chat_with_tools(agent_id, message, no_reflect, stream, json_mode)


def _chat_with_tools(agent_id: str, message: str, no_reflect: bool, stream, json_mode: bool):
    """Chat with full tool support."""
    from ...agent import Agent

    # Create agent with event sink
    agent = Agent(agent_id, event_sink=stream.sink)

    try:
        log_to_memory = not no_reflect
        response = agent.chat(message, log_to_memory=log_to_memory, save_to_history=False)

        if json_mode:
            print(json.dumps({
                "agent_id": agent_id,
                "response": response
            }))
        else:
            print_header("Response", json_mode)
            print()
            print(response)

    except Exception as e:
        print_error(str(e), json_mode)
        sys.exit(1)


def _chat_no_tools(agent_id: str, message: str, no_reflect: bool, stream, json_mode: bool):
    """Chat without tool execution - pure LLM response."""
    from ...agent import Agent
    from ...llms import get_client

    # Create agent for system prompt only
    agent = Agent(agent_id, event_sink=stream.sink)
    system_prompt = agent._build_system_prompt()

    stream.sink("chat_start", {"message_length": len(message), "no_tools": True})

    try:
        # Get client and call without tools
        client = get_client()

        config = agent._get_system_config()
        llm_config = config.get("llm", {})
        provider = llm_config.get("provider", "openai")
        provider_config = llm_config.get("providers", {}).get(provider, {})
        max_tokens = provider_config.get("max_output_tokens", 16000)

        response = client.create(
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": message}],
            tools=None,  # No tools
            agent_id=agent_id
        )

        stream.sink("llm_response", {
            "stop_reason": response.stop_reason,
            "usage": {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
        })

        # Extract text response
        text_response = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_response += block.text

        stream.sink("chat_end", {"response_length": len(text_response)})

        # Run reflection append if not disabled
        if not no_reflect and agent.reflection:
            agent.reflection.append(message, text_response)

        if json_mode:
            print(json.dumps({
                "agent_id": agent_id,
                "response": text_response,
                "no_tools": True
            }))
        else:
            print_header("Response (no tools)", json_mode)
            print()
            print(text_response)

    except Exception as e:
        print_error(str(e), json_mode)
        sys.exit(1)
