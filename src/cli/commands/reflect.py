"""
Reflect command - Trigger reflection phases manually.
"""

import json
import sys
from pathlib import Path
from typing import List

from ..formatters import print_header, print_error, print_success
from ..stream import SyncEventStream


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_reflect(args: List[str], json_mode: bool = False):
    """Trigger reflection for an agent.

    Usage:
      dev reflect <agent>              Run full reflection (append + consolidate)
      dev reflect <agent> --append     Run only append phase
      dev reflect <agent> --consolidate  Run only consolidate phase
    """
    if not args:
        print_error("Usage: dev reflect <agent> [--append|--consolidate]", json_mode)
        sys.exit(1)

    agent_id = args[0]
    append_only = "--append" in args
    consolidate_only = "--consolidate" in args

    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    # Create stream for events
    stream = SyncEventStream(json_mode)

    from ...agent import Agent

    # Create agent with event sink
    agent = Agent(agent_id, event_sink=stream.sink)

    if not agent.consolidation:
        print_error(f"Reflection not enabled for agent: {agent_id}", json_mode)
        sys.exit(1)

    try:
        if append_only:
            _run_append(agent, stream, json_mode)
        elif consolidate_only:
            _run_consolidate(agent, stream, json_mode)
        else:
            # Run both
            _run_append(agent, stream, json_mode)
            _run_consolidate(agent, stream, json_mode)

    except Exception as e:
        print_error(str(e), json_mode)
        sys.exit(1)


def _run_append(agent, stream, json_mode: bool):
    """Run the append phase.

    Append requires recent conversation data. We'll look for the most recent
    conversation in the agent's session files.
    """
    if not json_mode:
        print_header("Append Phase", json_mode)

    # Find most recent conversation
    conv_dir = AGENTS_DIR / agent.id / "state" / "conversation"
    if not conv_dir.exists():
        print_error("No conversation history found for append phase", json_mode)
        return

    # Get most recent session file
    session_files = sorted(conv_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not session_files:
        print_error("No conversation history found for append phase", json_mode)
        return

    recent_session = session_files[0]
    content = recent_session.read_text()

    # Parse last exchange (simplified parsing)
    user_msg, assistant_msg = _parse_last_exchange(content)

    if not user_msg or not assistant_msg:
        print_error("Could not parse last conversation exchange", json_mode)
        return

    if not json_mode:
        print(f"Using conversation from: {recent_session.name}")
        print(f"User message: {user_msg[:50]}...")

    # Run append
    agent.consolidation.append(user_msg, assistant_msg)

    if not json_mode:
        print_success("Append phase complete", json_mode)


def _run_consolidate(agent, stream, json_mode: bool):
    """Run the consolidate phase."""
    if not json_mode:
        print_header("Consolidate Phase", json_mode)

    # Run consolidate
    agent.consolidation.consolidate()

    if not json_mode:
        print_success("Consolidate phase complete", json_mode)


def _parse_last_exchange(content: str) -> tuple:
    """Parse the last user/assistant exchange from conversation markdown.

    Returns:
        Tuple of (user_message, assistant_message)
    """
    lines = content.split("\n")

    user_sections = []
    assistant_sections = []

    current_section = None
    current_lines = []

    for line in lines:
        if line.startswith("## User"):
            if current_section and current_lines:
                if current_section == "user":
                    user_sections.append("\n".join(current_lines))
                elif current_section == "assistant":
                    assistant_sections.append("\n".join(current_lines))
            current_section = "user"
            current_lines = []
        elif line.startswith("## Assistant"):
            if current_section and current_lines:
                if current_section == "user":
                    user_sections.append("\n".join(current_lines))
                elif current_section == "assistant":
                    assistant_sections.append("\n".join(current_lines))
            current_section = "assistant"
            current_lines = []
        elif current_section:
            current_lines.append(line)

    # Don't forget the last section
    if current_section and current_lines:
        if current_section == "user":
            user_sections.append("\n".join(current_lines))
        elif current_section == "assistant":
            assistant_sections.append("\n".join(current_lines))

    # Get last exchange
    user_msg = user_sections[-1].strip() if user_sections else None
    assistant_msg = assistant_sections[-1].strip() if assistant_sections else None

    return user_msg, assistant_msg
