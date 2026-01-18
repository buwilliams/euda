"""
Consolidate Phase - Heavy analysis for memory graduation and profile updates.

This phase runs on daily trigger to:
1. Analyze patterns in short-term and long-term memory
2. Graduate important short-term items to long-term memory
3. Update the agent's profile based on observed patterns
4. Create historical profile snapshots at year boundaries
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from ..llms import get_client
from ..events import emit_ui_event
from ..tools.data.memory import (
    _load_entries,
    _save_entries,
    _ensure_memory_dirs,
)
from ..tools.data.jobs import get_jobs_completed_by_agent
from ..metacognition.config import get_global_config

from .prompts import build_consolidate_prompt, get_consolidate_system_prompt

if TYPE_CHECKING:
    from .reflection import Reflection


# How many days of long-term memory to include for context
RECENT_MEMORY_DAYS = 7


def consolidate_phase(reflection: "Reflection", execution_id: str = None) -> Optional[dict]:
    """Run the consolidate phase for an agent.

    Performs heavy analysis to graduate memories and update profile.

    Args:
        reflection: The Reflection instance
        execution_id: Optional execution ID for SSE progress tracking

    Returns:
        Dict with items_graduated, profile_updated, long_term_entry counts/flags
    """
    agent_id = reflection.agent.id
    is_user = agent_id == "user"

    def emit_progress(step: str, message: str):
        """Emit SSE progress event."""
        emit_ui_event("reflection:progress", {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "phase": "consolidate",
            "step": step,
            "message": message
        })

    reflection.logger.info({
        "event": "consolidate_start",
        "agent_id": agent_id,
        "execution_id": execution_id
    })

    # Emit start event
    emit_progress("loading_data", "Loading memory and profile...")

    # Load short-term memory
    short_term_memory = _load_entries(agent_id)

    # Load recent long-term memory
    recent_long_term = _load_recent_long_term(reflection, days=RECENT_MEMORY_DAYS)

    # Load current profile
    current_profile = reflection.agent.profile

    # Load completed jobs for context
    completed_jobs = get_jobs_completed_by_agent(agent_id, limit=20)

    # Skip if no data to analyze
    if not short_term_memory and not recent_long_term and not completed_jobs:
        reflection.logger.info({
            "event": "consolidate_skip",
            "agent_id": agent_id,
            "reason": "no_data"
        })
        emit_ui_event("reflection:complete", {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "phase": "consolidate",
            "skipped": True
        })
        return {"items_graduated": 0, "profile_updated": False, "long_term_entry": False}

    emit_progress("building_prompt", "Analyzing patterns...")

    # Build prompt
    prompt = build_consolidate_prompt(
        agent_id=agent_id,
        agent_profile=current_profile,
        short_term_memory=short_term_memory,
        recent_long_term=recent_long_term,
        completed_jobs=completed_jobs,
        is_user=is_user
    )

    emit_progress("calling_llm", "Consulting AI...")

    # Call LLM
    client = get_client()
    reflection_config = get_global_config().get_reflection_config()
    response = client.create(
        max_tokens=reflection_config.get("consolidate_max_tokens", 2000),
        system=get_consolidate_system_prompt(is_user),
        messages=[{"role": "user", "content": prompt}],
        agent_id=f"{agent_id}/reflection"
    )

    # Extract text response
    text_response = ""
    for block in response.content:
        if hasattr(block, "text"):
            text_response += block.text

    # Emit LLM complete event with token counts
    emit_ui_event("reflection:llm_complete", {
        "execution_id": execution_id,
        "agent_id": agent_id,
        "phase": "consolidate",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens
    })

    reflection.logger.info({
        "event": "consolidate_llm_response",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "usage": {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens
        }
    })

    emit_progress("parsing_response", "Processing results...")

    # Parse reflection result
    result = _parse_consolidate_result(text_response)

    if result is None:
        reflection.logger.error({
            "event": "consolidate_parse_error",
            "agent_id": agent_id,
            "response": text_response[:500]
        })
        emit_ui_event("reflection:error", {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "phase": "consolidate",
            "error": "Failed to parse LLM response"
        })
        return {"items_graduated": 0, "profile_updated": False, "long_term_entry": False}

    emit_progress("applying_results", "Updating profile and memory...")

    # Apply long-term memory entry
    if result.get("long_term_entry"):
        _write_long_term_entry(reflection, result["long_term_entry"])

    # Apply profile updates
    if result.get("profile_updates"):
        _update_profile(reflection, result["profile_updates"])

    # Graduate specified items
    graduated_ids = result.get("graduate_ids", [])
    if graduated_ids:
        _graduate_items(reflection, short_term_memory, graduated_ids)

    # Check for year boundary and create historical snapshot
    _maybe_snapshot_profile(reflection)

    reflection.logger.info({
        "event": "consolidate_complete",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "long_term_entry": bool(result.get("long_term_entry")),
        "profile_updated": bool(result.get("profile_updates")),
        "items_graduated": len(graduated_ids)
    })

    # Emit completion event
    emit_ui_event("reflection:complete", {
        "execution_id": execution_id,
        "agent_id": agent_id,
        "phase": "consolidate",
        "items_graduated": len(graduated_ids),
        "profile_updated": bool(result.get("profile_updates")),
        "long_term_entry": bool(result.get("long_term_entry"))
    })

    return {
        "items_graduated": len(graduated_ids),
        "profile_updated": bool(result.get("profile_updates")),
        "long_term_entry": bool(result.get("long_term_entry"))
    }


def _load_recent_long_term(reflection: "Reflection", days: int) -> str:
    """Load recent long-term memory entries.

    Args:
        reflection: The Reflection instance
        days: Number of days to look back

    Returns:
        Combined content from recent long-term memory files
    """
    agent_id = reflection.agent.id
    today = datetime.now()
    content_parts = []

    for i in range(days):
        date = today - timedelta(days=i)
        year = date.strftime("%Y")
        date_str = date.strftime("%Y-%m-%d")

        # Try year-based path first, then legacy flat path
        year_path = reflection._get_long_term_dir(year) / f"{date_str}.md"
        legacy_path = reflection._get_long_term_dir().parent / f"{date_str}.md"

        memory_path = None
        if year_path.exists():
            memory_path = year_path
        elif legacy_path.exists():
            memory_path = legacy_path

        if memory_path:
            content_parts.append(memory_path.read_text())

    return "\n\n---\n\n".join(content_parts)


def _parse_consolidate_result(response: str) -> Optional[dict]:
    """Parse LLM response into consolidation result.

    Args:
        response: Raw LLM response text

    Returns:
        Dict with long_term_entry, profile_updates, graduate_ids
        or None if parsing fails
    """
    text = response.strip()

    # Handle markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                result = json.loads(text[start:end])
            except json.JSONDecodeError:
                return None
        else:
            return None

    if not isinstance(result, dict):
        return None

    # Normalize result
    return {
        "long_term_entry": result.get("long_term_entry"),
        "profile_updates": result.get("profile_updates"),
        "graduate_ids": result.get("graduate_ids", [])
    }


def _write_long_term_entry(reflection: "Reflection", content: str):
    """Write an entry to long-term memory.

    Uses year-based directory structure.

    Args:
        reflection: The Reflection instance
        content: Content to write
    """
    agent_id = reflection.agent.id
    today = datetime.now()
    year = today.strftime("%Y")
    date_str = today.strftime("%Y-%m-%d")

    # Ensure year directory exists
    long_term_dir = reflection._get_long_term_dir(year)
    long_term_dir.mkdir(parents=True, exist_ok=True)

    memory_path = long_term_dir / f"{date_str}.md"
    timestamp = today.strftime("%I:%M %p").lstrip("0")

    # Entry header
    entry_header = f"## {timestamp} · Reflection"

    # Append to existing or create new
    if memory_path.exists():
        existing = memory_path.read_text()
        new_content = f"{existing}\n\n{entry_header}\n\n{content}"
    else:
        new_content = f"# Long-term Memory - {date_str}\n\n{entry_header}\n\n{content}"

    memory_path.write_text(new_content)


def _update_profile(reflection: "Reflection", updates: str):
    """Update the agent's profile with new information.

    This appends a reflection section to the profile. The next consolidation
    will read this and incorporate it properly.

    Args:
        reflection: The Reflection instance
        updates: Description of updates to apply
    """
    profile_path = reflection._get_profile_path()

    if profile_path.exists():
        current_profile = profile_path.read_text()
    else:
        current_profile = f"# Profile: {reflection.agent.id}\n"

    # Add reflection update section
    today = datetime.now().strftime("%Y-%m-%d")
    update_section = f"\n\n---\n\n## Reflection Update ({today})\n\n{updates}"

    new_profile = current_profile + update_section
    profile_path.write_text(new_profile)


def _graduate_items(reflection: "Reflection", short_term_memory: List[dict], graduate_ids: List[str]):
    """Graduate specified items from short-term to long-term memory.

    Args:
        reflection: The Reflection instance
        short_term_memory: All short-term memory items
        graduate_ids: IDs of items to graduate
    """
    agent_id = reflection.agent.id
    today = datetime.now()
    year = today.strftime("%Y")
    date_str = today.strftime("%Y-%m-%d")

    # Find items to graduate
    to_graduate = [m for m in short_term_memory if m.get("id") in graduate_ids]

    if not to_graduate:
        return

    # Format graduation content
    lines = ["The following items have been marked for long-term preservation:", ""]

    for item in to_graduate:
        item_type = item.get("type", "idea")
        desc = item.get("short_description", "")
        date_mentioned = item.get("date_mentioned", "unknown")
        lines.append(f"- **{item_type.title()}**: {desc} (first mentioned {date_mentioned})")

    content = "\n".join(lines)

    # Write to long-term memory
    long_term_dir = reflection._get_long_term_dir(year)
    long_term_dir.mkdir(parents=True, exist_ok=True)

    memory_path = long_term_dir / f"{date_str}.md"
    timestamp = today.strftime("%I:%M %p").lstrip("0")
    entry_header = f"## {timestamp} · Graduated Memories"

    if memory_path.exists():
        existing = memory_path.read_text()
        new_content = f"{existing}\n\n{entry_header}\n\n{content}"
    else:
        new_content = f"# Long-term Memory - {date_str}\n\n{entry_header}\n\n{content}"

    memory_path.write_text(new_content)


def _maybe_snapshot_profile(reflection: "Reflection"):
    """Create historical profile snapshot if at year boundary.

    Checks if we're in a new year and the previous year's snapshot doesn't exist.

    Args:
        reflection: The Reflection instance
    """
    today = datetime.now()
    current_year = today.strftime("%Y")
    previous_year = str(int(current_year) - 1)

    # Check if we're in first week of year and previous year snapshot doesn't exist
    if today.month == 1 and today.day <= 7:
        historical_path = reflection._get_historical_profile_path(previous_year)
        current_path = reflection._get_profile_path()

        if not historical_path.exists() and current_path.exists():
            # Create snapshot of current profile as previous year's historical
            current_profile = current_path.read_text()
            historical_path.write_text(current_profile)

            reflection.logger.info({
                "event": "profile_snapshot_created",
                "agent_id": reflection.agent.id,
                "year": previous_year
            })
