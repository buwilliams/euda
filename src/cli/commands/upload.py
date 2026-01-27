"""
Upload command - Upload files to agent inbox or topic.
"""

import json
import sys
from pathlib import Path
from typing import List

from ..formatters import print_error, print_success


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def cmd_upload(args: List[str], json_mode: bool = False):
    """Upload a file to an agent inbox or topic.

    Usage:
      dev upload <agent_id> <file>     Create topic with file for agent
      dev upload topic-xxx <file>      Add file to existing topic
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

    # Determine if target is a topic ID or agent ID
    if target.startswith("topic-"):
        _upload_to_topic(target, file_path, json_mode)
    else:
        _upload_to_agent(target, file_path, json_mode)


def _upload_to_topic(topic_id: str, file_path: Path, json_mode: bool):
    """Upload file to an existing topic."""
    from plugins.core.data.topics import get_topic
    from plugins.core.data.assets import write_asset

    # Verify topic exists
    topic = get_topic(topic_id)
    if not topic:
        print_error(f"Topic not found: {topic_id}", json_mode)
        sys.exit(1)

    # Read file content
    try:
        content = file_path.read_text()
    except UnicodeDecodeError:
        print_error("Only text files are supported for upload", json_mode)
        sys.exit(1)

    # Write asset
    result = write_asset(topic_id, file_path.name, content)

    if "error" in result:
        print_error(result["error"], json_mode)
        sys.exit(1)

    if json_mode:
        print(json.dumps({
            "topic_id": topic_id,
            "filename": file_path.name,
            "status": result.get("status", "success")
        }))
    else:
        print_success(f"Uploaded {file_path.name} to topic {topic_id}", json_mode)


def _upload_to_agent(agent_id: str, file_path: Path, json_mode: bool):
    """Create a topic for the agent with the file attached."""
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

    from plugins.core.data.topics import create_topic, get_agent_inbox_topic
    from plugins.core.data.assets import write_asset

    # Create topic under agent's inbox
    inbox = get_agent_inbox_topic(agent_id)
    parent_id = inbox["id"] if inbox else None

    topic = create_topic(
        name=f"Process file: {file_path.name}",
        description=f"File uploaded via dev CLI: {file_path.name}",
        parent_id=parent_id,
        assignee=agent_id,
        tags=["dev:upload"],
        created_by="dev-cli"
    )

    topic_id = topic["id"]

    # Write asset
    result = write_asset(topic_id, file_path.name, content)

    if "error" in result:
        print_error(result["error"], json_mode)
        sys.exit(1)

    if json_mode:
        print(json.dumps({
            "topic_id": topic_id,
            "agent_id": agent_id,
            "filename": file_path.name,
            "status": "created"
        }))
    else:
        print_success(f"Created topic {topic_id} for {agent_id} with file {file_path.name}", json_mode)
