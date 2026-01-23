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
      dev prompt <agent> system         Show system prompt
      dev prompt <agent> job <job_id>   Show prompt for a specific job
      dev prompt <agent> reflect        Show reflection prompt
      dev prompt <agent> explore        Show exploration prompt
    """
    if len(args) < 2:
        print_error("Usage: dev prompt <agent> <system|job|reflect|explore> [job_id]", json_mode)
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
    elif prompt_type == "job":
        if len(args) < 3:
            print_error("Usage: dev prompt <agent> job <job_id>", json_mode)
            sys.exit(1)
        job_id = args[2]
        _show_job_prompt(agent_id, job_id, json_mode)
    elif prompt_type == "reflect":
        _show_reflect_prompt(agent_id, json_mode)
    elif prompt_type == "explore":
        _show_explore_prompt(agent_id, json_mode)
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


def _show_job_prompt(agent_id: str, job_id: str, json_mode: bool):
    """Show the prompt that would be sent for a job."""
    from ...agent import Agent
    from ...tools.data.jobs import get_job

    job = get_job(job_id)
    if not job:
        print_error(f"Job not found: {job_id}", json_mode)
        sys.exit(1)

    # Create agent without event sink (read-only)
    agent = Agent(agent_id)
    job_prompt = agent._format_job_prompt(job)
    prompt_type = agent._get_job_prompt_type(job)

    if json_mode:
        print(json.dumps({
            "agent_id": agent_id,
            "job_id": job_id,
            "job_name": job.get("name"),
            "template": prompt_type,
            "prompt": job_prompt
        }))
    else:
        print_header(f"Job Prompt: {job.get('name', job_id)}", json_mode)
        print(f"Template: {prompt_type}")
        print()
        print(job_prompt)


def _show_reflect_prompt(agent_id: str, json_mode: bool):
    """Show the reflection prompt template."""
    from ...prompts import render_template

    # Create a fake reflection job to show the prompt
    prompt = render_template(
        "agent/consolidation",
        agent_id=agent_id,
        job_id="<job_id>",
        job_name="Trigger:consolidation:2025-01-01",
        job_description="Daily reflection trigger",
        job_due_date="No deadline",
        job_tags="trigger:consolidation",
        job_attachments="No attachments",
        remaining_jobs_notice=""
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


def _show_explore_prompt(agent_id: str, json_mode: bool):
    """Show the exploration prompt template."""
    from ...prompts import render_template
    from ...tools.data.memory import get_memory_for_prompt

    # Get actual user memory to show what would be included
    user_memory = get_memory_for_prompt("user")
    if not user_memory:
        user_memory = "(No items currently in user's memory)"

    # Create a fake exploration job to show the prompt
    prompt = render_template(
        "agent/exploration",
        agent_id=agent_id,
        job_id="<job_id>",
        job_name="Trigger:exploration:2025-01-01",
        job_description="Scheduled exploration",
        job_due_date="No deadline",
        job_tags="trigger:exploration",
        job_attachments="No attachments",
        remaining_jobs_notice="",
        user_memory=user_memory
    )

    if json_mode:
        print(json.dumps({
            "agent_id": agent_id,
            "prompt_type": "exploration",
            "template": "agent/exploration",
            "prompt": prompt
        }))
    else:
        print_header(f"Exploration Prompt Template: {agent_id}", json_mode)
        print()
        print(prompt)
