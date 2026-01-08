"""
Knowledge Tools - Read Euno documentation and agent logs.

Provides safe access to docs, specs, agent personas, and logs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from . import tool


PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "data"
AGENTS_DIR = DATA_DIR / "agents"

# Safe directories that can be read
SAFE_DIRS = {
    "docs": PROJECT_DIR / "docs",
    "spec": PROJECT_DIR / "spec",
}


@tool("list_euno_docs", "List all Euno documentation and spec files")
def list_euno_docs() -> dict:
    """List all available documentation and spec files.

    Returns:
        Dictionary with docs and specs lists
    """
    result = {
        "docs": [],
        "specs": [],
        "agent_personas": []
    }

    # List docs
    docs_dir = SAFE_DIRS["docs"]
    if docs_dir.exists():
        for f in sorted(docs_dir.glob("*.md")):
            result["docs"].append({
                "name": f.name,
                "path": f"docs/{f.name}"
            })

    # List specs
    spec_dir = SAFE_DIRS["spec"]
    if spec_dir.exists():
        for f in sorted(spec_dir.glob("*.md")):
            result["specs"].append({
                "name": f.name,
                "path": f"spec/{f.name}"
            })

    # List agent personas
    if AGENTS_DIR.exists():
        for agent_dir in sorted(AGENTS_DIR.iterdir()):
            if agent_dir.is_dir():
                persona_path = agent_dir / f"{agent_dir.name}-persona.md"
                if persona_path.exists():
                    result["agent_personas"].append({
                        "agent": agent_dir.name,
                        "path": f"data/agents/{agent_dir.name}/{agent_dir.name}-persona.md"
                    })

    return result


@tool("read_euno_doc", "Read a Euno documentation, spec, or agent persona file")
def read_euno_doc(path: str) -> dict:
    """Read a documentation file from safe directories.

    Args:
        path: Relative path like 'docs/1_pitch.md', 'spec/1_agents.md',
              or 'data/agents/friend/friend-persona.md'

    Returns:
        File content or error message
    """
    # Normalize path
    path = path.strip()
    if path.startswith("/"):
        path = path[1:]

    # Check if it's a safe path
    allowed = False
    full_path = None

    # Check docs/
    if path.startswith("docs/"):
        full_path = PROJECT_DIR / path
        if full_path.suffix == ".md":
            allowed = True

    # Check spec/
    elif path.startswith("spec/"):
        full_path = PROJECT_DIR / path
        if full_path.suffix == ".md":
            allowed = True

    # Check agent personas
    elif path.startswith("data/agents/") and path.endswith("-persona.md"):
        full_path = PROJECT_DIR / path
        allowed = True

    if not allowed:
        return {
            "error": "Access denied. Only docs/*.md, spec/*.md, and agent persona files are readable.",
            "allowed_paths": [
                "docs/*.md",
                "spec/*.md",
                "data/agents/{agent}/{agent}-persona.md"
            ]
        }

    if not full_path.exists():
        return {"error": f"File not found: {path}"}

    try:
        content = full_path.read_text()
        return {
            "path": path,
            "content": content
        }
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}


@tool("read_agent_logs", "Read recent logs for an agent")
def read_agent_logs(agent_id: str, date: str = None, limit: int = 50) -> dict:
    """Read recent log entries for an agent.

    Args:
        agent_id: The agent whose logs to read
        date: Date in YYYY-MM-DD format (default: today)
        limit: Maximum number of entries to return (default: 50)

    Returns:
        List of log entries or error message
    """
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        return {"error": f"Agent not found: {agent_id}"}

    logs_dir = agent_dir / "logs"
    if not logs_dir.exists():
        return {"agent_id": agent_id, "entries": [], "message": "No logs found"}

    # Determine which log file to read
    if date:
        log_file = logs_dir / f"{date}.jsonl"
    else:
        # Use today's date
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = logs_dir / f"{today}.jsonl"

    if not log_file.exists():
        # Try to find the most recent log file
        log_files = sorted(logs_dir.glob("*.jsonl"), reverse=True)
        if log_files:
            log_file = log_files[0]
        else:
            return {"agent_id": agent_id, "entries": [], "message": "No logs found"}

    # Read the log file
    entries = []
    try:
        with open(log_file) as f:
            lines = f.readlines()
            # Get last N entries
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        return {"error": f"Failed to read logs: {str(e)}"}

    return {
        "agent_id": agent_id,
        "log_file": log_file.name,
        "entries": entries,
        "total_entries": len(entries)
    }
