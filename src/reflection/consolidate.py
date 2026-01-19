"""
Consolidate Phase - Heavy analysis for memory graduation and identity updates.

This phase runs on daily trigger to:
1. Analyze patterns in short-term and long-term memory (via RLM)
2. Graduate important short-term items to long-term memory
3. Update the agent's identity based on observed patterns
4. Create historical identity snapshots at year boundaries
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
from ..rlm import RLMClient, load_long_term_memory

from .prompts import build_consolidate_prompt, get_consolidate_system_prompt

if TYPE_CHECKING:
    from .reflection import Reflection


# How many days of long-term memory to analyze via RLM
RLM_MEMORY_DAYS = 30


def consolidate_phase(reflection: "Reflection", execution_id: str = None) -> Optional[dict]:
    """Run the consolidate phase for an agent.

    Performs heavy analysis to graduate memories and update identity.

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
    emit_progress("loading_data", "Loading memory and identity...")

    # Load short-term memory
    short_term_memory = _load_entries(agent_id)

    # Use RLM to analyze long-term memory patterns (30-day window)
    recent_long_term = _analyze_long_term_with_rlm(reflection, days=RLM_MEMORY_DAYS)

    # Load current identity
    current_profile = reflection.agent.identity

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

    emit_progress("applying_results", "Updating identity and memory...")

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


def _analyze_long_term_with_rlm(reflection: "Reflection", days: int) -> str:
    """Analyze long-term memory using RLM for consolidation insights.

    Uses RLM to semantically analyze memory and extract relevant patterns,
    allowing analysis of a larger time window than direct context loading.

    Args:
        reflection: The Reflection instance
        days: Number of days to analyze

    Returns:
        RLM-generated insights about memory patterns, or empty string if no memory
    """
    agent_id = reflection.agent.id

    # Load memory for RLM
    memory = load_long_term_memory(agent_id=agent_id, days=days)

    # If no memory entries, return empty
    if memory["metadata"]["total_entries"] == 0:
        return ""

    # Use RLM to analyze patterns for consolidation
    rlm = RLMClient(agent_id=agent_id)
    result = rlm.analyze(
        query=(
            "What patterns, themes, learnings, and significant events from recent memory "
            "should inform identity updates? Focus on:\n"
            "1. Recurring goals or concerns\n"
            "2. Notable achievements or setbacks\n"
            "3. Changes in interests or priorities\n"
            "4. Important relationships or people mentioned\n"
            "5. Key decisions or turning points"
        ),
        memory=memory,
        time_range_days=days
    )

    if result.error:
        reflection.logger.warning({
            "event": "rlm_analysis_error",
            "agent_id": agent_id,
            "error": result.error
        })
        return ""

    return result.findings


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


# Identity section definitions - maps JSON keys to markdown headers
IDENTITY_SECTIONS = {
    "purpose": "Purpose",
    "behavioral_rules": "Behavioral Rules",
    "voice": "Voice",
    "wants_and_fears": "Wants and Fears",
    "stable_attractors": "Stable Attractors",
    "notable_events": "Notable Events",
    "influences": "Influences",
    "interests": "Interests",
    "biographical_information": "Biographical Information",
}

# Section display order
SECTION_ORDER = [
    "purpose",
    "behavioral_rules",
    "voice",
    "wants_and_fears",
    "stable_attractors",
    "notable_events",
    "influences",
    "interests",
    "biographical_information",
]


def _parse_identity_sections(content: str) -> tuple[str, dict]:
    """Parse an identity markdown into title and sections.

    Handles various identity formats:
    - Structured identities with # Title and ## Sections
    - Legacy identities with unstructured content
    - Identities with "Reflection Update" sections to migrate

    Args:
        content: The identity markdown content

    Returns:
        Tuple of (title_line, sections_dict) where sections_dict maps
        section keys to their content
    """
    import re

    lines = content.split("\n")
    title = ""
    sections = {}
    preamble = []  # Content before any section headers

    # Extract title (first # line)
    title_found = False
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line
            lines = lines[i + 1:]
            title_found = True
            break

    # If no title found, all lines are potential content
    if not title_found:
        lines = content.split("\n")

    # Build reverse mapping from headers to keys
    header_to_key = {v.lower(): k for k, v in IDENTITY_SECTIONS.items()}

    current_section = None
    current_content = []
    in_preamble = True  # Track content before first section

    for line in lines:
        # Check for section header (## Something)
        if line.startswith("## "):
            in_preamble = False

            # Save previous section
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()

            # Parse new section
            header_text = line[3:].strip()
            # Remove any date suffix like "(2025-01-18)"
            header_clean = re.sub(r'\s*\([^)]*\)\s*$', '', header_text).strip()
            current_section = header_to_key.get(header_clean.lower())

            # If not a recognized section, store under special key
            if not current_section:
                # Check for "Reflection Update" sections - these should be migrated
                if header_clean.lower().startswith("reflection update"):
                    current_section = "_reflection_update"
                else:
                    current_section = f"_other_{header_text}"

            current_content = []
        elif in_preamble:
            preamble.append(line)
        elif current_section:
            current_content.append(line)

    # Save last section
    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    # Handle preamble content (unstructured legacy content)
    preamble_text = "\n".join(preamble).strip()
    if preamble_text:
        # Store as behavioral observations that can be organized later
        sections["_preamble"] = preamble_text

    return title, sections


def _build_identity_markdown(title: str, sections: dict, agent_id: str) -> str:
    """Build identity markdown from title and sections.

    Args:
        title: The title line (e.g., "# User" or "# Chat")
        sections: Dict mapping section keys to content
        agent_id: Agent ID for default title

    Returns:
        Complete identity markdown
    """
    if not title:
        title = f"# {agent_id.title()}"

    lines = [title, ""]

    # Add preamble as introductory text if present (legacy unstructured content)
    if "_preamble" in sections and sections["_preamble"].strip():
        lines.append(sections["_preamble"])
        lines.append("")

    # Add sections in defined order
    for key in SECTION_ORDER:
        if key in sections and sections[key].strip():
            header = IDENTITY_SECTIONS[key]
            lines.append(f"## {header}")
            lines.append("")
            lines.append(sections[key])
            lines.append("")

    # Add any "other" sections (like Core Promise) at the end
    # Skip _preamble (already handled) and _reflection_update (deprecated)
    for key, content in sections.items():
        if key.startswith("_other_") and content.strip():
            header = key.replace("_other_", "")
            lines.append(f"## {header}")
            lines.append("")
            lines.append(content)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _merge_section_content(existing: str, new_content: str) -> str:
    """Merge new content into an existing section.

    Handles different content formats:
    - Lists (bullet points): Appends new items, avoiding duplicates
    - Prose: Appends with paragraph break

    Args:
        existing: Existing section content
        new_content: New content to merge

    Returns:
        Merged content
    """
    if not existing.strip():
        return new_content.strip()

    if not new_content.strip():
        return existing.strip()

    existing = existing.strip()
    new_content = new_content.strip()

    # Check if content is list-based (starts with - or *)
    existing_is_list = existing.lstrip().startswith(("-", "*", "I must", "I must not", "Wants:", "Fears:"))
    new_is_list = new_content.lstrip().startswith(("-", "*", "I must", "I must not", "Wants:", "Fears:"))

    if existing_is_list or new_is_list:
        # For lists, check for duplicates before appending
        existing_lines = set(line.strip().lower() for line in existing.split("\n") if line.strip())
        new_lines = []

        for line in new_content.split("\n"):
            if line.strip() and line.strip().lower() not in existing_lines:
                new_lines.append(line)

        if new_lines:
            return existing + "\n" + "\n".join(new_lines)
        return existing
    else:
        # For prose, append with paragraph break
        return existing + "\n\n" + new_content


def _update_profile(reflection: "Reflection", updates):
    """Update the agent's identity with new information.

    Handles both structured updates (dict mapping section keys to content)
    and legacy string updates (for backwards compatibility).

    Args:
        reflection: The Reflection instance
        updates: Either a dict of section updates or a string description
    """
    identity_path = reflection._get_identity_path()
    agent_id = reflection.agent.id

    # Load current identity
    if identity_path.exists():
        current_identity = identity_path.read_text()
    else:
        current_identity = f"# {agent_id.title()}\n"

    # Handle legacy string updates (backwards compatibility)
    if isinstance(updates, str):
        today = datetime.now().strftime("%Y-%m-%d")
        update_section = f"\n\n---\n\n## Reflection Update ({today})\n\n{updates}"
        new_identity = current_identity + update_section
        identity_path.write_text(new_identity)
        return

    # Handle structured dict updates
    if not isinstance(updates, dict) or not updates:
        return

    # Parse existing identity into sections
    title, sections = _parse_identity_sections(current_identity)

    # Merge updates into sections
    for key, content in updates.items():
        if key in IDENTITY_SECTIONS and content:
            existing = sections.get(key, "")
            sections[key] = _merge_section_content(existing, content)

    # Build and write new identity
    new_identity = _build_identity_markdown(title, sections, agent_id)
    identity_path.write_text(new_identity)


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
        historical_path = reflection._get_historical_identity_path(previous_year)
        current_path = reflection._get_identity_path()

        if not historical_path.exists() and current_path.exists():
            # Create snapshot of current identity as previous year's historical
            current_identity = current_path.read_text()
            historical_path.write_text(current_identity)

            reflection.logger.info({
                "event": "identity_snapshot_created",
                "agent_id": reflection.agent.id,
                "year": previous_year
            })
