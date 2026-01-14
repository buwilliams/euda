"""
Job command - Create and run jobs with streaming output.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from ..formatters import print_header, print_error, print_success
from ..stream import EventStream, SyncEventStream


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_job(args: List[str], json_mode: bool = False):
    """Create a job and run it immediately.

    Usage:
      dev job <agent> <task>          Create job and run
      dev job <agent> <task> --no-reflect    Skip reflection
      dev job <agent> <task> --dry-run       Show prompt only
      dev job <agent> <task> --max-iterations N
    """
    # Parse flags
    no_reflect = "--no-reflect" in args
    dry_run = "--dry-run" in args
    max_iterations = None

    # Extract max-iterations
    clean_args = []
    i = 0
    while i < len(args):
        if args[i] == "--no-reflect":
            i += 1
        elif args[i] == "--dry-run":
            i += 1
        elif args[i] == "--max-iterations":
            if i + 1 < len(args):
                try:
                    max_iterations = int(args[i + 1])
                except ValueError:
                    print_error("--max-iterations requires a number", json_mode)
                    sys.exit(1)
                i += 2
            else:
                print_error("--max-iterations requires a value", json_mode)
                sys.exit(1)
        else:
            clean_args.append(args[i])
            i += 1

    if len(clean_args) < 2:
        print_error("Usage: dev job <agent> <task> [--no-reflect] [--dry-run]", json_mode)
        sys.exit(1)

    agent_id = clean_args[0]
    task = " ".join(clean_args[1:])

    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    # Create the job
    from ...tools.data.jobs import create_job, get_system_container

    system_container = get_system_container()

    job = create_job(
        name=task[:100],  # Truncate name
        description=task if len(task) > 100 else None,
        parent_id=system_container["id"],
        assignees=[agent_id],
        tags=["dev:manual"],
        created_by="dev-cli"
    )

    job_id = job["id"]

    if not json_mode:
        print_success(f"Created job: {job_id}", json_mode)

    if dry_run:
        # Show prompt without executing
        from ...agent import Agent
        agent = Agent(agent_id)
        prompt = agent._format_job_prompt(job)

        if json_mode:
            print(json.dumps({
                "job_id": job_id,
                "agent_id": agent_id,
                "prompt": prompt,
                "dry_run": True
            }))
        else:
            print_header("Prompt (dry run)", json_mode)
            print(prompt)
        return

    # Run the job with streaming
    _run_job(agent_id, job, no_reflect, max_iterations, json_mode)


def cmd_run(args: List[str], json_mode: bool = False):
    """Run an existing job.

    Usage:
      dev run <agent> <job_id>
      dev run <agent> <job_id> --no-reflect
    """
    no_reflect = "--no-reflect" in args
    clean_args = [a for a in args if a != "--no-reflect"]

    if len(clean_args) < 2:
        print_error("Usage: dev run <agent> <job_id> [--no-reflect]", json_mode)
        sys.exit(1)

    agent_id = clean_args[0]
    job_id = clean_args[1]

    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    # Get the job
    from ...tools.data.jobs import get_job

    job = get_job(job_id)
    if not job:
        print_error(f"Job not found: {job_id}", json_mode)
        sys.exit(1)

    _run_job(agent_id, job, no_reflect, None, json_mode)


def _run_job(agent_id: str, job: dict, no_reflect: bool, max_iterations: int, json_mode: bool):
    """Run a job with streaming output."""
    from ...agent import Agent

    # Create event stream
    stream = EventStream(json_mode)

    # Create agent with event sink
    agent = Agent(agent_id, event_sink=stream.sink)

    # Start streaming
    stream.start()

    try:
        # Set job context
        agent.set_job_context(job["id"])

        # Format prompt
        prompt = agent._format_job_prompt(job)

        # Get max iterations from config or override
        if max_iterations is None:
            config = agent._get_system_config()
            max_iterations = config.get("agents", {}).get("max_work_iterations", 20)

        # Run work cycle
        from ...prompts import load_template

        iteration = 0
        while not agent._work_done and iteration < max_iterations:
            iteration += 1
            stream.sink("work_iteration", {"iteration": iteration})

            # Determine whether to log to memory
            log_to_memory = not no_reflect

            response = agent.chat(prompt, log_to_memory=log_to_memory, save_to_history=False)

            if agent._work_done:
                break

            # Continue prompt for subsequent iterations
            prompt = load_template("agent/continue")

        # Final status
        reason = "done_working" if agent._work_done else "max_iterations"
        stream.sink("work_cycle_end", {
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
