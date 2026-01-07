"""
Memory Tools - Track important items for proactive attention.

Storage: JSONL file at data/user/memory.jsonl
Entries are valid for 3 months from date_mentioned.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from . import tool


DATA_DIR = Path(__file__).parent.parent.parent / "data"
USER_DIR = DATA_DIR / "user"
MEMORY_FILE = USER_DIR / "memory.jsonl"

VALID_TYPES = {"person", "place", "thing", "goal", "concern", "idea"}
VALIDITY_DAYS = 90  # 3 months


def _ensure_user_dir():
    """Ensure user directory exists."""
    USER_DIR.mkdir(parents=True, exist_ok=True)


def _load_entries() -> List[dict]:
    """Load all memory entries."""
    _ensure_user_dir()
    entries = []
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return entries


def _save_entries(entries: List[dict]):
    """Save all entries to file."""
    _ensure_user_dir()
    with open(MEMORY_FILE, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')


def _is_valid(entry: dict) -> bool:
    """Check if an entry is still valid (within 3 months)."""
    try:
        mentioned = datetime.strptime(entry['date_mentioned'], '%Y-%m-%d')
        cutoff = datetime.now() - timedelta(days=VALIDITY_DAYS)
        return mentioned >= cutoff
    except (KeyError, ValueError):
        return False


@tool("add_memory", "Add an item to the user's memory for proactive attention")
def add_memory(
    short_description: str,
    type: str,
    date_expected: str = None
) -> dict:
    """Add a memory entry.

    Args:
        short_description: Brief description of what to remember (person, place, goal, etc.)
        type: Category - one of: person, place, thing, goal, concern, idea
        date_expected: Optional expected date (YYYY-MM-DD) when this becomes relevant

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

    entries = _load_entries()
    entries.append(entry)
    _save_entries(entries)

    return entry


@tool("list_memory", "List all valid memory items for context")
def list_memory() -> List[dict]:
    """Get all valid (non-expired) memory entries.

    Entries older than 3 months are automatically pruned.
    """
    entries = _load_entries()
    # Filter to only valid entries and clean up expired ones
    valid = [e for e in entries if _is_valid(e)]

    # If we filtered any, save the cleaned list
    if len(valid) != len(entries):
        _save_entries(valid)

    return valid


@tool("remove_memory", "Remove a memory item by ID")
def remove_memory(entry_id: str) -> dict:
    """Remove a memory entry.

    Args:
        entry_id: The ID of the entry to remove (e.g., mem-abc12345)
    """
    entries = _load_entries()
    original_count = len(entries)
    entries = [e for e in entries if e.get('id') != entry_id]

    if len(entries) == original_count:
        return {"error": f"Entry not found: {entry_id}"}

    _save_entries(entries)
    return {"removed": entry_id}


def get_memory_for_prompt() -> str:
    """Get formatted memory items for inclusion in system prompt.

    This is called by the Agent class when building system prompts.
    Returns empty string if no items.
    """
    entries = list_memory()
    if not entries:
        return ""

    lines = ["## Memory", "", "Items the user has mentioned that may be relevant:", ""]

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
