"""
Memory Tools - Track important items for proactive attention.

Every agent (including user) has:
- Short-term memory: JSONL file at data/agents/{agent_id}/memory/short-term.jsonl (90-day rolling)
- Long-term memory: Markdown files at data/agents/{agent_id}/memory/long-term/{date}.md (indefinite)

Long-term memory access is mediated by RLM (Recursive Language Model) which allows
semantic search and pattern analysis without loading full history into context.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .. import tool
from ...agent.rlm import RLMClient, load_long_term_memory


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"

VALID_TYPES = {"person", "place", "thing", "goal", "concern", "idea", "learning", "behavior", "interest"}
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
    to become part of the agent's identity over time via consolidation.
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

    # Create trigger topics for agents subscribed to long-term memory updates
    if agent_id == "user":
        from .topics import create_topic, list_topics, get_agent_inbox_topic
        from ..agents.agents import list_agents

        for agent_config in list_agents():
            if agent_config.get("state", "enabled") == "disabled":
                continue
            if "memory:long-term" in agent_config.get("triggers", []):
                topic_name = f"euno:memory-long-term:{date}"

                # Check if trigger topic already exists for this agent today
                existing = list_topics(status="todo", assignee=agent_config["id"])
                already_exists = any(t["name"] == topic_name for t in existing)

                if not already_exists:
                    # Create topic under agent's inbox
                    inbox = get_agent_inbox_topic(agent_config["id"])
                    parent_id = inbox["id"] if inbox else None

                    create_topic(
                        name=topic_name,
                        description="New long-term memory entry to process",
                        parent_id=parent_id,
                        assignee=agent_config["id"],
                        due_date=None,
                        created_by="system"
                    )

    return {"date": date, "agent_id": agent_id, "status": "added", "source": source}


@tool("graduate_memory", "Graduate a short-term memory item to long-term memory. Use when: an item is important enough to preserve permanently.", tool_type="data")
def graduate_memory(memory_id: str, reason: str = None, agent_id: str = "user") -> dict:
    """Move a short-term memory item to long-term memory.

    Args:
        memory_id: The ID of the memory item to graduate (e.g., mem-abc12345)
        reason: Optional reason for graduating this item
        agent_id: Agent ID (defaults to "user")
    """
    entries = _load_entries(agent_id)

    # Find the entry
    entry = None
    remaining = []
    for e in entries:
        if e.get('id') == memory_id:
            entry = e
        else:
            remaining.append(e)

    if not entry:
        return {"error": f"Memory item not found: {memory_id}"}

    # Format for long-term memory
    item_type = entry.get('type', 'idea')
    desc = entry.get('short_description', '')
    date_mentioned = entry.get('date_mentioned', 'unknown')

    content_lines = [
        f"**Graduated Memory ({item_type})**: {desc}",
        f"- First mentioned: {date_mentioned}"
    ]
    if entry.get('date_expected'):
        content_lines.append(f"- Expected: {entry['date_expected']}")
    if reason:
        content_lines.append(f"- Reason for graduating: {reason}")

    content = "\n".join(content_lines)

    # Write to long-term memory
    write_long_term_memory(content=content, agent_id=agent_id, source="Reflection")

    # Remove from short-term
    _save_entries(remaining, agent_id)

    return {
        "graduated": memory_id,
        "type": item_type,
        "description": desc,
        "reason": reason
    }


@tool("recall_memory", "Recall information from long-term memory using semantic search. Use when: you need to remember something from the past.", tool_type="data")
def recall_memory(
    query: str,
    time_range_days: int = 365,
    agent_id: str = "user"
) -> dict:
    """RLM-powered memory recall.

    Uses a Recursive Language Model to semantically search long-term memory.
    The LLM writes code to explore memory and uses sub-LLM calls for analysis.

    Args:
        query: What to recall (semantic, not keyword match)
        time_range_days: How far back to search (default: 1 year)
        agent_id: Whose memory to search

    Returns:
        {
            "query": "...",
            "findings": "Synthesized answer from memory",
            "sources": [{"date": "...", "snippet": "..."}],
            "iterations": 5,
            "sub_calls": 3,
            "error": null
        }
    """
    # Load memory for the specified time range
    memory = load_long_term_memory(agent_id=agent_id, days=time_range_days)

    if memory["metadata"]["total_entries"] == 0:
        return {
            "query": query,
            "findings": "No long-term memory entries found.",
            "sources": [],
            "iterations": 0,
            "sub_calls": 0,
            "error": None
        }

    # Run RLM session
    rlm = RLMClient(agent_id=agent_id)
    result = rlm.recall(query, memory, time_range_days)

    return {
        "query": result.query,
        "findings": result.findings,
        "sources": result.sources,
        "iterations": result.iterations,
        "sub_calls": result.sub_calls,
        "error": result.error
    }


@tool("analyze_memory", "Analyze patterns and trends in long-term memory. Use when: you need to understand how things have changed over time.", tool_type="data")
def analyze_memory(
    query: str,
    time_range_days: int = 365,
    agent_id: str = "user"
) -> dict:
    """Deep analysis of memory patterns.

    Uses a Recursive Language Model to analyze patterns, trends, and evolution
    across long-term memory entries.

    Args:
        query: What pattern to analyze
        time_range_days: Analysis window (default: 1 year)
        agent_id: Whose memory to analyze

    Examples:
        - "What recurring concerns appear in my memory?"
        - "How have my goals evolved over the past year?"
        - "What people have I mentioned most frequently?"

    Returns:
        {
            "query": "...",
            "findings": "Analysis of patterns found",
            "sources": [...],
            "iterations": 8,
            "sub_calls": 5,
            "error": null
        }
    """
    # Load memory for the specified time range
    memory = load_long_term_memory(agent_id=agent_id, days=time_range_days)

    if memory["metadata"]["total_entries"] == 0:
        return {
            "query": query,
            "findings": "No long-term memory entries found for analysis.",
            "sources": [],
            "iterations": 0,
            "sub_calls": 0,
            "error": None
        }

    # Run RLM session
    rlm = RLMClient(agent_id=agent_id)
    result = rlm.analyze(query, memory, time_range_days)

    return {
        "query": result.query,
        "findings": result.findings,
        "sources": result.sources,
        "iterations": result.iterations,
        "sub_calls": result.sub_calls,
        "error": result.error
    }


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
