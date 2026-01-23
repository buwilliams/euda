"""
Consolidate Phase - Identity evolution from long-term memory.

This phase runs on daily trigger to:
1. Use RLM extract_identity() to analyze long-term memory for identity updates
2. Update the agent's identity based on observed patterns
3. Create historical identity snapshots at year boundaries

Architecture Note:
Long-term memory is the PRIMARY store. Identity is derived from long-term
memory via RLM, eliminating the need to "graduate" short-term items.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from .....events import emit_ui_event
from ....rlm import RLMClient, load_long_term_memory

if TYPE_CHECKING:
    from .consolidation import Consolidation


# How many days of long-term memory to analyze via RLM
RLM_MEMORY_DAYS = 30


def consolidate_phase(consolidation: "Consolidation", execution_id: str = None) -> Optional[dict]:
    """Run the consolidate phase for an agent.

    Performs heavy analysis to update identity based on long-term memory.
    Uses RLM extract_identity() for intelligent identity evolution.

    Architecture note: With long-term memory as the primary store,
    we no longer need to "graduate" short-term items. Identity is
    derived directly from long-term memory via RLM.

    Args:
        consolidation: The Consolidation instance
        execution_id: Optional execution ID for SSE progress tracking

    Returns:
        Dict with identity_updated flag
    """
    agent_id = consolidation.agent.id

    def emit_progress(step: str, message: str):
        """Emit SSE progress event."""
        emit_ui_event("consolidation:progress", {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "phase": "consolidate",
            "step": step,
            "message": message
        })

    consolidation.logger.info({
        "event": "consolidate_start",
        "agent_id": agent_id,
        "execution_id": execution_id
    })

    # Emit start event
    emit_progress("loading_data", "Loading memory and identity...")

    # Load memory for RLM analysis
    memory = load_long_term_memory(agent_id=agent_id, days=RLM_MEMORY_DAYS)

    # Skip if no memory to analyze
    if memory["metadata"]["total_entries"] == 0:
        consolidation.logger.info({
            "event": "consolidate_skip",
            "agent_id": agent_id,
            "reason": "no_memory"
        })
        emit_ui_event("consolidation:complete", {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "phase": "consolidate",
            "skipped": True
        })
        return {"identity_updated": False}

    # Load current identity
    current_identity = consolidation.agent.identity

    emit_progress("identity_analysis", "Analyzing memory for identity updates via RLM...")

    # Use RLM to extract identity updates directly from long-term memory
    rlm = RLMClient(agent_id=agent_id)
    identity_result = rlm.extract_identity(memory, current_identity)

    identity_updates = None
    if not identity_result.error and identity_result.findings:
        # Parse the structured identity updates
        identity_updates = _parse_identity_updates(identity_result.findings)

    consolidation.logger.info({
        "event": "rlm_identity_analysis",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "has_updates": identity_updates is not None,
        "rlm_iterations": identity_result.iterations,
        "rlm_sub_calls": identity_result.sub_calls,
        "error": identity_result.error
    })

    emit_progress("applying_results", "Updating identity...")

    # Apply identity updates from RLM
    identity_updated = False
    if identity_updates and identity_updates.get("sections"):
        _update_identity(consolidation, identity_updates["sections"])
        identity_updated = True

    # Check for year boundary and create historical snapshot
    _maybe_snapshot_identity(consolidation)

    consolidation.logger.info({
        "event": "consolidate_complete",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "identity_updated": identity_updated
    })

    # Emit completion event
    emit_ui_event("consolidation:complete", {
        "execution_id": execution_id,
        "agent_id": agent_id,
        "phase": "consolidate",
        "identity_updated": identity_updated
    })

    return {"identity_updated": identity_updated}


def _parse_identity_updates(findings: str) -> Optional[dict]:
    """Parse identity updates from RLM extract_identity() findings.

    Args:
        findings: JSON string from RLM

    Returns:
        Parsed dict with "sections" and "reasoning" keys, or None
    """
    import json as json_module

    findings = findings.strip()

    # Handle markdown code blocks
    if findings.startswith("```"):
        lines = findings.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        findings = "\n".join(lines)

    # If it starts with { and ends with }, try direct parse
    if findings.startswith("{") and findings.endswith("}"):
        try:
            return json_module.loads(findings)
        except json_module.JSONDecodeError:
            pass

    # Try to find JSON object in the text
    import re
    match = re.search(r'\{[\s\S]*\}', findings)
    if match:
        try:
            return json_module.loads(match.group(0))
        except json_module.JSONDecodeError:
            pass

    return None


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


def _update_identity(consolidation: "Consolidation", updates):
    """Update the agent's identity with new information.

    Handles both structured updates (dict mapping section keys to content)
    and legacy string updates (for backwards compatibility).

    Args:
        consolidation: The Consolidation instance
        updates: Either a dict of section updates or a string description
    """
    identity_path = consolidation._get_identity_path()
    agent_id = consolidation.agent.id

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


def _maybe_snapshot_identity(consolidation: "Consolidation"):
    """Create historical identity snapshot if at year boundary.

    Checks if we're in a new year and the previous year's snapshot doesn't exist.

    Args:
        consolidation: The Consolidation instance
    """
    today = datetime.now()
    current_year = today.strftime("%Y")
    previous_year = str(int(current_year) - 1)

    # Check if we're in first week of year and previous year snapshot doesn't exist
    if today.month == 1 and today.day <= 7:
        historical_path = consolidation._get_historical_identity_path(previous_year)
        current_path = consolidation._get_identity_path()

        if not historical_path.exists() and current_path.exists():
            # Create snapshot of current identity as previous year's historical
            current_identity = current_path.read_text()
            historical_path.write_text(current_identity)

            consolidation.logger.info({
                "event": "identity_snapshot_created",
                "agent_id": consolidation.agent.id,
                "year": previous_year
            })
