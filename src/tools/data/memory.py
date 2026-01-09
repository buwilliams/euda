"""
Memory Tools - Track important items for proactive attention.

Every agent (including user) has:
- Short-term memory: JSONL file at data/agents/{agent_id}/memory/short-term.jsonl (90-day rolling)
- Long-term memory: Markdown files at data/agents/{agent_id}/memory/long-term/{date}.md (indefinite)
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .. import tool


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"

VALID_TYPES = {"person", "place", "thing", "goal", "concern", "idea"}
VALIDITY_DAYS = 90  # 3 months


# =============================================================================
# Path helpers
# =============================================================================

def _get_short_term_path(agent_id: str = "user") -> Path:
    """Get path to agent's short-term memory file."""
    return AGENTS_DIR / agent_id / "memory" / "short-term.jsonl"


def _get_long_term_dir(agent_id: str = "user", year: str = None) -> Path:
    """Get path to agent's long-term memory directory (year-based).

    Args:
        agent_id: Agent ID
        year: Specific year (YYYY) or None for current year
    """
    base = AGENTS_DIR / agent_id / "memory" / "long-term"
    if year:
        return base / year
    return base / datetime.now().strftime("%Y")


def _ensure_memory_dirs(agent_id: str = "user"):
    """Ensure memory directories exist for an agent."""
    memory_dir = AGENTS_DIR / agent_id / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "long-term").mkdir(exist_ok=True)


# =============================================================================
# Short-term memory helpers
# =============================================================================

def _load_entries(agent_id: str = "user") -> List[dict]:
    """Load all short-term memory entries for an agent."""
    _ensure_memory_dirs(agent_id)
    entries = []
    path = _get_short_term_path(agent_id)
    if path.exists():
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return entries


def _save_entries(entries: List[dict], agent_id: str = "user"):
    """Save all short-term memory entries for an agent."""
    _ensure_memory_dirs(agent_id)
    path = _get_short_term_path(agent_id)
    with open(path, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')


def _is_valid(entry: dict) -> bool:
    """Check if an entry is still valid (within 90 days)."""
    try:
        mentioned = datetime.strptime(entry['date_mentioned'], '%Y-%m-%d')
        cutoff = datetime.now() - timedelta(days=VALIDITY_DAYS)
        return mentioned >= cutoff
    except (KeyError, ValueError):
        return False


def _archive_expired_memories(expired: List[dict], agent_id: str = "user"):
    """Archive expired short-term memories to long-term memory.

    This preserves memories that roll off after 90 days, allowing them
    to become part of the agent's profile over time via the Profiler.
    """
    # Group by type for readable formatting
    by_type = {}
    for entry in expired:
        t = entry.get('type', 'idea')
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(entry)

    # Format the archive content
    lines = ["The following memory items have rolled off after 90 days:", ""]

    for entry_type in sorted(by_type.keys()):
        lines.append(f"**{entry_type.title()}s:**")
        for entry in by_type[entry_type]:
            desc = entry.get('short_description', '')
            date_mentioned = entry.get('date_mentioned', 'unknown')
            date_expected = entry.get('date_expected')

            if date_expected:
                lines.append(f"- {desc} (first mentioned {date_mentioned}, expected {date_expected})")
            else:
                lines.append(f"- {desc} (first mentioned {date_mentioned})")
        lines.append("")

    content = "\n".join(lines).rstrip()
    write_long_term_memory(content=content, agent_id=agent_id, source="Memory")


# =============================================================================
# Short-term memory tools
# =============================================================================

@tool("add_memory", "Add an item to short-term memory for proactive attention (expires in 90 days). Use when: user mentions something worth tracking - a person, goal, concern, or upcoming event.", tool_type="data")
def add_memory(
    short_description: str,
    type: str,
    date_expected: str = None,
    agent_id: str = "user"
) -> dict:
    """Add a short-term memory entry.

    Args:
        short_description: Brief description of what to remember (person, place, goal, etc.)
        type: Category - one of: person, place, thing, goal, concern, idea
        date_expected: Optional expected date (YYYY-MM-DD) when this becomes relevant
        agent_id: Agent ID (defaults to "user")

    Returns:
        The created entry
    """
    if type not in VALID_TYPES:
        return {"error": f"Invalid type. Must be one of: {', '.join(sorted(VALID_TYPES))}"}

    entry = {
        "id": f"mem-{uuid.uuid4().hex[:8]}",
        "date_mentioned": datetime.now().strftime('%Y-%m-%d'),
        "date_expected": date_expected,
        "type": type,
        "short_description": short_description
    }

    entries = _load_entries(agent_id)
    entries.append(entry)
    _save_entries(entries, agent_id)

    return entry


@tool("list_memory", "List all valid short-term memory items (people, places, goals, concerns). Use when: need context about what's on someone's mind or active concerns.", tool_type="data")
def list_memory(agent_id: str = "user") -> List[dict]:
    """Get all valid (non-expired) short-term memory entries for an agent.

    Entries older than 90 days are archived to long-term memory and pruned.

    Args:
        agent_id: Agent ID (defaults to "user")
    """
    entries = _load_entries(agent_id)
    valid = [e for e in entries if _is_valid(e)]
    expired = [e for e in entries if not _is_valid(e)]

    # Archive expired entries to long-term memory before removing them
    if expired:
        _archive_expired_memories(expired, agent_id)
        _save_entries(valid, agent_id)

    return valid


@tool("remove_memory", "Remove a short-term memory item by ID. Use when: item is no longer relevant or was added by mistake.", tool_type="data")
def remove_memory(entry_id: str, agent_id: str = "user") -> dict:
    """Remove a short-term memory entry.

    Args:
        entry_id: The ID of the entry to remove (e.g., mem-abc12345)
        agent_id: Agent ID (defaults to "user")
    """
    entries = _load_entries(agent_id)
    original_count = len(entries)
    entries = [e for e in entries if e.get('id') != entry_id]

    if len(entries) == original_count:
        return {"error": f"Entry not found: {entry_id}"}

    _save_entries(entries, agent_id)
    return {"removed": entry_id}


# =============================================================================
# Long-term memory tools
# =============================================================================

@tool("read_long_term_memory", "Read long-term memory entries for a date. Use when: need historical context about what happened on a specific day.", tool_type="data")
def read_long_term_memory(date: str = None, agent_id: str = "user") -> dict:
    """Read long-term memory entries.

    Args:
        date: Specific date (YYYY-MM-DD) or None for today
        agent_id: Agent ID (defaults to "user")
    """
    _ensure_memory_dirs(agent_id)

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    year = date[:4]  # Extract year from date

    # Try year-based path first
    long_term_dir = _get_long_term_dir(agent_id, year)
    memory_path = long_term_dir / f"{date}.md"

    # Fall back to legacy flat path for backward compatibility
    if not memory_path.exists():
        legacy_dir = AGENTS_DIR / agent_id / "memory" / "long-term"
        legacy_path = legacy_dir / f"{date}.md"
        if legacy_path.exists():
            memory_path = legacy_path

    if memory_path.exists():
        return {
            "date": date,
            "agent_id": agent_id,
            "content": memory_path.read_text(),
            "exists": True
        }
    return {
        "date": date,
        "agent_id": agent_id,
        "content": "",
        "exists": False
    }


@tool("write_long_term_memory", "Add an entry to long-term memory. Use when: recording significant events or conversations.", tool_type="data")
def write_long_term_memory(content: str, date: str = None, agent_id: str = "user", source: str = None) -> dict:
    """Add an entry to long-term memory.

    Args:
        content: The content to add
        date: Specific date (YYYY-MM-DD) or None for today
        agent_id: Agent ID (defaults to "user")
        source: Who/what is writing the entry (e.g., "User", "Worker", "Friend")
    """
    _ensure_memory_dirs(agent_id)

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    if source is None:
        source = agent_id.title()

    year = date[:4]  # Extract year from date

    # Use year-based directory structure
    long_term_dir = _get_long_term_dir(agent_id, year)
    long_term_dir.mkdir(parents=True, exist_ok=True)

    memory_path = long_term_dir / f"{date}.md"
    timestamp = datetime.now().strftime("%I:%M %p").lstrip("0")  # 2:30 PM format

    # Entry header with time and source
    entry_header = f"## {timestamp} · {source}"

    # Append to existing or create new
    if memory_path.exists():
        existing = memory_path.read_text()
        new_content = f"{existing}\n\n{entry_header}\n\n{content}"
    else:
        new_content = f"# Long-term Memory - {date}\n\n{entry_header}\n\n{content}"

    memory_path.write_text(new_content)

    # Create trigger jobs for agents subscribed to long-term memory updates
    # Only trigger if this is the user's long-term memory (for backward compat with lifelog:new)
    if agent_id == "user":
        from .jobs import create_job, list_jobs
        from ..agents.agents import list_agents

        for agent_config in list_agents():
            if not agent_config.get("enabled", True):
                continue
            if "lifelog:new" in agent_config.get("triggers", []):
                job_name = f"Trigger:lifelog-new:{date}"

                # Check if trigger job already exists for this agent today
                existing = list_jobs(status="todo", assignee=agent_config["id"])
                already_exists = any(j["name"] == job_name for j in existing)

                if not already_exists:
                    create_job(
                        name=job_name,
                        description="New long-term memory entry to process",
                        assignees=[agent_config["id"]],
                        tags=["trigger:lifelog-new"],
                        due_date=None,
                        created_by="system"
                    )

    return {"date": date, "agent_id": agent_id, "status": "added", "source": source}


@tool("list_long_term_memory_dates", "List all dates with long-term memory entries. Use when: finding available historical records.", tool_type="data")
def list_long_term_memory_dates(agent_id: str = "user") -> List[str]:
    """List all dates that have long-term memory entries for an agent.

    Args:
        agent_id: Agent ID (defaults to "user")
    """
    _ensure_memory_dirs(agent_id)

    base_dir = AGENTS_DIR / agent_id / "memory" / "long-term"
    if not base_dir.exists():
        return []

    dates = []

    # Check year directories (new structure)
    for year_dir in base_dir.iterdir():
        if year_dir.is_dir() and year_dir.name.isdigit() and len(year_dir.name) == 4:
            for path in year_dir.glob("*.md"):
                dates.append(path.stem)

    # Also check flat structure (legacy) for backward compatibility
    for path in base_dir.glob("*.md"):
        if path.stem not in dates:
            dates.append(path.stem)

    dates.sort(reverse=True)
    return dates


# =============================================================================
# Helper for system prompts (not a tool)
# =============================================================================

def get_memory_for_prompt(agent_id: str = "user") -> str:
    """Get formatted short-term memory items for inclusion in system prompt.

    This is called by the Agent class when building system prompts.
    Returns empty string if no items.
    """
    entries = list_memory(agent_id)
    if not entries:
        return ""

    lines = ["## Memory", "", "Items that may be relevant:", ""]

    # Sort by type for readability
    entries_by_type = {}
    for entry in entries:
        t = entry.get('type', 'idea')
        if t not in entries_by_type:
            entries_by_type[t] = []
        entries_by_type[t].append(entry)

    for entry_type in sorted(entries_by_type.keys()):
        for entry in entries_by_type[entry_type]:
            date_info = f"(mentioned {entry['date_mentioned']}"
            if entry.get('date_expected'):
                date_info += f", expected {entry['date_expected']}"
            date_info += ")"
            lines.append(f"- **{entry_type}**: {entry['short_description']} {date_info}")

    return "\n".join(lines)
