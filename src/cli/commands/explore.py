"""
Explore command - Trigger exploration for an agent.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from ..formatters import print_header, print_error, print_success
from ..stream import EventStream


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_explore(args: List[str], json_mode: bool = False):
    """Create and run exploration job for an agent.

    Usage:
      dev explore <agent>
    """
    if not args:
        print_error("Usage: dev explore <agent>", json_mode)
        sys.exit(1)

    agent_id = args[0]

    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    # Create exploration job
    from ...llms.tools.data.jobs import create_job, get_system_container

    today = datetime.now().strftime("%Y-%m-%d")
    system_container = get_system_container()

    job = create_job(
        name=f"Trigger:exploration:{today}",
        description="Manual exploration trigger from dev CLI",
        parent_id=system_container["id"],
        assignees=[agent_id],
        tags=["trigger:exploration", "dev:manual"],
        created_by="dev-cli"
    )

    if not json_mode:
        print_success(f"Created exploration job: {job['id']}", json_mode)

    # Create event stream
    stream = EventStream(json_mode)

    from ...agent import Agent

    # Create agent with event sink
    agent = Agent(agent_id, event_sink=stream.sink)

    # Start streaming
    stream.start()

    try:
        # Set job context
        agent.set_job_context(job["id"])

        # Format prompt using exploration template
        prompt = agent._format_job_prompt(job)

        # Get max iterations from config
        config = agent._get_system_config()
        max_iterations = config.get("agents", {}).get("max_work_iterations", 20)

        # Run work cycle
        from ...prompts import load_template

        iteration = 0
        while not agent._work_done and iteration < max_iterations:
            iteration += 1
            stream.sink("work_iteration", {"iteration": iteration})

            response = agent.chat(prompt, log_to_memory=True, save_to_history=False)

            if agent._work_done:
                break

            # Continue prompt for subsequent iterations
            prompt = load_template("agent/continue")

        # Final status
        reason = "done_working" if agent._work_done else "max_iterations"
        stream.sink("exploration_complete", {
            "reason": reason,
            "iterations": iteration,
            "job_id": job["id"]
        })

    except KeyboardInterrupt:
        stream.sink("interrupted", {"job_id": job["id"]})
        if not json_mode:
            print("\nInterrupted")

    except Exception as e:
        stream.sink("error", {"error": str(e), "job_id": job["id"]})
        print_error(str(e), json_mode)

    finally:
        agent.clear_job_context()
        stream.flush()
