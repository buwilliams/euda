"""
Prompt command - Inspect prompts that would be sent to agents.
"""

import json
import sys
from pathlib import Path
from typing import List

from ..formatters import print_header, print_error


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_prompt(args: List[str], json_mode: bool = False):
    """Show prompts that would be sent to agents.

    Usage:
      dev prompt <agent> system             Show system prompt
      dev prompt <agent> topic <topic_id>   Show prompt for a specific topic
      dev prompt <agent> reflect            Show reflection prompt
    """
    if len(args) < 2:
        print_error("Usage: dev prompt <agent> <system|topic|reflect> [topic_id]", json_mode)
        sys.exit(1)

    agent_id = args[0]
    prompt_type = args[1]

    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    if prompt_type == "system":
        _show_system_prompt(agent_id, json_mode)
    elif prompt_type == "topic":
        if len(args) < 3:
            print_error("Usage: dev prompt <agent> topic <topic_id>", json_mode)
            sys.exit(1)
        topic_id = args[2]
        _show_topic_prompt(agent_id, topic_id, json_mode)
    elif prompt_type == "reflect":
        _show_reflect_prompt(agent_id, json_mode)
    else:
        print_error(f"Unknown prompt type: {prompt_type}", json_mode)
        sys.exit(1)


def _show_system_prompt(agent_id: str, json_mode: bool):
    """Show the system prompt that would be sent."""
    from ...agent import Agent

    # Create agent without event sink (read-only)
    agent = Agent(agent_id)
    system_prompt = agent._build_system_prompt()

    if json_mode:
        print(json.dumps({
            "agent_id": agent_id,
            "prompt_type": "system",
            "prompt": system_prompt
        }))
    else:
        print_header(f"System Prompt: {agent_id}", json_mode)
        print()
        print(system_prompt)


def _show_topic_prompt(agent_id: str, topic_id: str, json_mode: bool):
    """Show the prompt that would be sent for a topic."""
    from ...agent import Agent
    from ...tools.data.topics import get_topic

    topic = get_topic(topic_id)
    if not topic:
        print_error(f"Topic not found: {topic_id}", json_mode)
        sys.exit(1)

    # Create agent without event sink (read-only)
    agent = Agent(agent_id)
    topic_prompt = agent._format_topic_prompt(topic)
    prompt_type = agent._get_topic_prompt_type(topic)

    if json_mode:
        print(json.dumps({
            "agent_id": agent_id,
            "topic_id": topic_id,
            "topic_name": topic.get("name"),
            "template": prompt_type,
            "prompt": topic_prompt
        }))
    else:
        print_header(f"Topic Prompt: {topic.get('name', topic_id)}", json_mode)
        print(f"Template: {prompt_type}")
        print()
        print(topic_prompt)


def _show_reflect_prompt(agent_id: str, json_mode: bool):
    """Show the reflection prompt template."""
    from ...prompts import render_template

    # Create a fake reflection topic to show the prompt
    prompt = render_template(
        "agent/consolidation",
        agent_id=agent_id,
        topic_id="<topic_id>",
        topic_name="euno:consolidate",
        topic_description="Daily reflection trigger",
        topic_due_date="No deadline",
        topic_tags="",
        topic_attachments="No attachments",
        remaining_topics_notice=""
    )

    if json_mode:
        print(json.dumps({
            "agent_id": agent_id,
            "prompt_type": "reflection",
            "template": "agent/consolidation",
            "prompt": prompt
        }))
    else:
        print_header(f"Reflection Prompt Template: {agent_id}", json_mode)
        print()
        print(prompt)


