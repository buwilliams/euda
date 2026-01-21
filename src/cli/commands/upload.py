"""
Upload command - Upload files to agent inbox or job.
"""

import json
import sys
from pathlib import Path
from typing import List

from ..formatters import print_error, print_success


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_upload(args: List[str], json_mode: bool = False):
    """Upload a file to an agent inbox or job.

    Usage:
      dev upload <agent_id> <file>     Create job with file for agent
      dev upload job-xxx <file>        Add file to existing job
    """
    if len(args) < 2:
        print_error("Usage: dev upload <target> <file>", json_mode)
        sys.exit(1)

    target = args[0]
    file_path = Path(args[1])

    # Validate file exists
    if not file_path.exists():
        print_error(f"File not found: {file_path}", json_mode)
        sys.exit(1)

    # Determine if target is a job ID or agent ID
    if target.startswith("job-"):
        _upload_to_job(target, file_path, json_mode)
    else:
        _upload_to_agent(target, file_path, json_mode)


def _upload_to_job(job_id: str, file_path: Path, json_mode: bool):
    """Upload file to an existing job."""
    from ...tools.data.jobs import get_job
    from ...tools.data.assets import write_asset

    # Verify job exists
    job = get_job(job_id)
    if not job:
        print_error(f"Job not found: {job_id}", json_mode)
        sys.exit(1)

    # Read file content
    try:
        content = file_path.read_text()
    except UnicodeDecodeError:
        print_error("Only text files are supported for upload", json_mode)
        sys.exit(1)

    # Write asset
    result = write_asset(job_id, file_path.name, content)

    if "error" in result:
        print_error(result["error"], json_mode)
        sys.exit(1)

    if json_mode:
        print(json.dumps({
            "job_id": job_id,
            "filename": file_path.name,
            "status": result.get("status", "success")
        }))
    else:
        print_success(f"Uploaded {file_path.name} to job {job_id}", json_mode)


def _upload_to_agent(agent_id: str, file_path: Path, json_mode: bool):
    """Create a job for the agent with the file attached."""
    # Check agent exists
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print_error(f"Agent not found: {agent_id}", json_mode)
        sys.exit(1)

    # Read file content
    try:
        content = file_path.read_text()
    except UnicodeDecodeError:
        print_error("Only text files are supported for upload", json_mode)
        sys.exit(1)

    from ...tools.data.jobs import create_job, get_system_container
    from ...tools.data.assets import write_asset

    # Create job
    system_container = get_system_container()

    job = create_job(
        name=f"Process file: {file_path.name}",
        description=f"File uploaded via dev CLI: {file_path.name}",
        parent_id=system_container["id"],
        assignees=[agent_id],
        tags=["dev:upload"],
        created_by="dev-cli"
    )

    job_id = job["id"]

    # Write asset
    result = write_asset(job_id, file_path.name, content)

    if "error" in result:
        print_error(result["error"], json_mode)
        sys.exit(1)

    if json_mode:
        print(json.dumps({
            "job_id": job_id,
            "agent_id": agent_id,
            "filename": file_path.name,
            "status": "created"
        }))
    else:
        print_success(f"Created job {job_id} for {agent_id} with file {file_path.name}", json_mode)
