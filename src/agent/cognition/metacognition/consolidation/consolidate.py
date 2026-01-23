"""
Consolidate Phase - Identity evolution and pattern discovery.

This phase runs on daily trigger to:
1. Run multi-pass pattern discovery (temporal, correlation, trajectory)
2. Use RLM extract_identity() to analyze long-term memory for identity updates
3. Update the agent's identity based on observed patterns
4. Create historical identity snapshots at year boundaries

Architecture Note:
Long-term memory is the PRIMARY store. Identity is derived from long-term
memory via RLM, eliminating the need to "graduate" short-term items.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from .....events import emit_ui_event
from ...regulation.config import get_global_config
from ....rlm import RLMClient, load_long_term_memory

from .patterns import (
    load_patterns,
    save_patterns,
    create_empty_patterns,
    format_patterns_for_prompt,
    cleanup_expired_hypotheses,
    update_confidence,
    apply_confidence_decay,
    find_similar_temporal,
    find_similar_correlation,
    find_trajectory_by_subject,
    TemporalPattern,
    Correlation,
    Trajectory,
    Hypothesis,
    add_temporal_pattern,
    add_correlation,
    add_trajectory,
    add_hypothesis,
    get_pending_hypotheses,
    validate_hypothesis,
)

if TYPE_CHECKING:
    from .consolidation import Consolidation


# How many days of long-term memory to analyze via RLM
RLM_MEMORY_DAYS = 30


def consolidate_phase(consolidation: "Consolidation", execution_id: str = None) -> Optional[dict]:
    """Run the consolidate phase for an agent.

    Performs heavy analysis to update identity based on long-term memory.
    Uses RLM extract_identity() for intelligent identity evolution.
    Includes multi-pass pattern discovery for improved user modeling.

    Architecture note: With long-term memory as the primary store,
    we no longer need to "graduate" short-term items. Identity is
    derived directly from long-term memory via RLM.

    Args:
        reflection: The Reflection instance
        execution_id: Optional execution ID for SSE progress tracking

    Returns:
        Dict with profile_updated, long_term_entry, patterns_discovered counts/flags
    """
    agent_id = consolidation.agent.id
    is_user = agent_id == "user"

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
    emit_progress("loading_data", "Loading memory, identity, and patterns...")

    # Load existing patterns
    pattern_store = load_patterns(agent_id)

    # Clean up expired hypotheses
    expired_hypotheses = cleanup_expired_hypotheses(pattern_store)
    if expired_hypotheses:
        consolidation.logger.info({
            "event": "hypotheses_expired",
            "agent_id": agent_id,
            "count": len(expired_hypotheses)
        })

    # Load memory for RLM analysis
    memory = load_long_term_memory(agent_id=agent_id, days=RLM_MEMORY_DAYS)

    # Check if patterns are enabled
    patterns_config = get_global_config().get_full_config().get("patterns", {})
    patterns_enabled = patterns_config.get("enabled", True)

    # Run multi-pass pattern discovery if enabled and we have memory
    patterns_discovered = 0
    patterns_decayed = 0
    validated_ids = set()
    if patterns_enabled and memory["metadata"]["total_entries"] > 0:
        emit_progress("pattern_discovery", "Running multi-pass pattern discovery...")
        patterns_discovered, validated_ids = _run_pattern_discovery(
            reflection, memory, pattern_store, patterns_config
        )

        # Apply confidence decay to patterns that weren't validated this cycle
        emit_progress("pattern_decay", "Applying confidence decay to unvalidated patterns...")
        patterns_decayed = apply_confidence_decay(pattern_store, validated_ids)
        if patterns_decayed > 0:
            consolidation.logger.info({
                "event": "patterns_decayed",
                "agent_id": agent_id,
                "count": patterns_decayed
            })

    # Skip if no memory to analyze
    if memory["metadata"]["total_entries"] == 0:
        # Still save patterns if any were discovered
        if patterns_discovered > 0:
            save_patterns(agent_id, pattern_store)

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
        return {"profile_updated": False, "long_term_entry": False, "patterns_discovered": patterns_discovered}

    # Load current identity
    current_profile = consolidation.agent.identity

    emit_progress("identity_analysis", "Analyzing memory for identity updates via RLM...")

    # Use RLM to extract identity updates directly from long-term memory
    rlm = RLMClient(agent_id=agent_id)
    identity_result = rlm.extract_identity(memory, current_profile)

    profile_updates = None
    if not identity_result.error and identity_result.findings:
        # Parse the structured identity updates
        profile_updates = _parse_identity_updates(identity_result.findings)

    consolidation.logger.info({
        "event": "rlm_identity_analysis",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "has_updates": profile_updates is not None,
        "rlm_iterations": identity_result.iterations,
        "rlm_sub_calls": identity_result.sub_calls,
        "error": identity_result.error
    })

    emit_progress("applying_results", "Updating identity...")

    # Apply profile updates from RLM
    profile_updated = False
    if profile_updates and profile_updates.get("sections"):
        _update_profile(reflection, profile_updates["sections"])
        profile_updated = True

    # Check for year boundary and create historical snapshots
    _maybe_snapshot_profile(reflection)
    if patterns_enabled:
        _maybe_snapshot_patterns(reflection, pattern_store)

    # Save updated patterns
    if patterns_enabled:
        save_patterns(agent_id, pattern_store)

    consolidation.logger.info({
        "event": "consolidate_complete",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "profile_updated": profile_updated,
        "patterns_discovered": patterns_discovered
    })

    # Emit completion event
    emit_ui_event("consolidation:complete", {
        "execution_id": execution_id,
        "agent_id": agent_id,
        "phase": "consolidate",
        "profile_updated": profile_updated,
        "long_term_entry": False,  # No longer writing reflection entries to long-term
        "patterns_discovered": patterns_discovered
    })

    return {
        "profile_updated": profile_updated,
        "long_term_entry": False,
        "patterns_discovered": patterns_discovered
    }


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


def _run_pattern_discovery(
    consolidation: "Consolidation",
    memory: dict,
    pattern_store,
    config: dict
) -> tuple:
    """Run multi-pass pattern discovery using RLM.

    Args:
        reflection: The Reflection instance
        memory: Pre-loaded memory data
        pattern_store: Existing pattern store to update
        config: Patterns configuration

    Returns:
        Tuple of (new_patterns_count, validated_pattern_ids)
    """
    agent_id = consolidation.agent.id
    rlm = RLMClient(agent_id=agent_id)

    # Get which passes to run
    discovery_passes = config.get("discovery_passes", ["temporal", "correlation", "trajectory"])
    min_evidence = config.get("min_evidence_for_pattern", 3)

    # Run multi-pass discovery
    try:
        discovered = rlm.discover_patterns(
            memory=memory,
            pattern_types=discovery_passes
        )
    except Exception as e:
        consolidation.logger.warning({
            "event": "pattern_discovery_error",
            "agent_id": agent_id,
            "error": str(e)
        })
        return (0, set())

    new_patterns = 0
    validated_ids = set()  # Track which patterns were validated this cycle

    # Process temporal patterns
    for raw_pattern in discovered.get("temporal", []):
        description = raw_pattern.get("description", "")
        granularity = raw_pattern.get("granularity", "daily")

        # Check if similar pattern exists
        existing = find_similar_temporal(pattern_store, description, granularity)
        if existing:
            # Update confidence on existing pattern
            update_confidence(existing, validated=True)
            validated_ids.add(existing["id"])
        else:
            # Create new pattern (starts as hypothesis if not enough evidence)
            evidence_count = raw_pattern.get("evidence_count", 1)
            if evidence_count >= min_evidence:
                pattern = TemporalPattern.create(
                    description=description,
                    granularity=granularity,
                    time_window=raw_pattern.get("time_window", {})
                )
                pattern.confidence = min(0.6, 0.3 + (evidence_count * 0.1))
                pattern.evidence_count = evidence_count
                add_temporal_pattern(pattern_store, pattern)
                validated_ids.add(pattern.id)  # New patterns are validated
                new_patterns += 1
            else:
                # Create hypothesis instead
                hypothesis = Hypothesis.create(
                    hypothesis_type="temporal",
                    hypothesis=f"{granularity.title()} pattern: {description}",
                    evidence_required=min_evidence
                )
                hypothesis.evidence_collected = evidence_count
                add_hypothesis(pattern_store, hypothesis)

    # Process correlations
    for raw_corr in discovered.get("correlations", []):
        items = raw_corr.get("items", [])
        description = raw_corr.get("description", "")

        existing = find_similar_correlation(pattern_store, items)
        if existing:
            update_confidence(existing, validated=True)
            validated_ids.add(existing["id"])
        else:
            correlation = Correlation.create(
                correlation_type=raw_corr.get("type", "co_occurrence"),
                items=items,
                description=description,
                lag_days=raw_corr.get("lag_days", 0)
            )
            add_correlation(pattern_store, correlation)
            validated_ids.add(correlation.id)  # New patterns are validated
            new_patterns += 1

    # Process trajectories
    for raw_traj in discovered.get("trajectories", []):
        subject = raw_traj.get("subject", "")

        existing = find_trajectory_by_subject(pattern_store, subject)
        if existing:
            # Add new stages to existing trajectory
            new_stages = raw_traj.get("stages", [])
            existing_dates = {s["date"] for s in existing.get("stages", [])}
            for stage in new_stages:
                if stage.get("date") not in existing_dates:
                    existing["stages"].append(stage)
            existing["stages"].sort(key=lambda s: s["date"])
            existing["direction"] = raw_traj.get("direction", existing.get("direction", "clarifying"))
            update_confidence(existing, validated=True)
            validated_ids.add(existing["id"])
        else:
            trajectory = Trajectory.create(
                trajectory_type=raw_traj.get("type", "goal_evolution"),
                subject=subject,
                initial_state=raw_traj.get("stages", [{}])[0].get("state", ""),
                direction=raw_traj.get("direction", "clarifying")
            )
            if len(raw_traj.get("stages", [])) > 1:
                trajectory.stages = raw_traj["stages"]
            add_trajectory(pattern_store, trajectory)
            validated_ids.add(trajectory.id)  # New patterns are validated
            new_patterns += 1

    consolidation.logger.info({
        "event": "pattern_discovery_complete",
        "agent_id": agent_id,
        "new_patterns": new_patterns,
        "validated_count": len(validated_ids),
        "temporal": len(discovered.get("temporal", [])),
        "correlations": len(discovered.get("correlations", [])),
        "trajectories": len(discovered.get("trajectories", []))
    })

    return (new_patterns, validated_ids)


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


def _update_profile(consolidation: "Consolidation", updates):
    """Update the agent's identity with new information.

    Handles both structured updates (dict mapping section keys to content)
    and legacy string updates (for backwards compatibility).

    Args:
        reflection: The Reflection instance
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


def _maybe_snapshot_profile(consolidation: "Consolidation"):
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


def _maybe_snapshot_patterns(consolidation: "Consolidation", pattern_store):
    """Create historical pattern snapshot if at year boundary.

    Preserves pattern state at year boundaries for tracking pattern evolution
    over time. Mirrors the identity snapshot behavior.

    Args:
        reflection: The Reflection instance
        pattern_store: Current PatternStore to snapshot
    """
    today = datetime.now()
    current_year = today.strftime("%Y")
    previous_year = str(int(current_year) - 1)

    # Check if we're in first week of year
    if today.month == 1 and today.day <= 7:
        agent_id = consolidation.agent.id
        from .patterns import _get_patterns_dir, _ensure_patterns_dir

        patterns_dir = _get_patterns_dir(agent_id)
        historical_file = patterns_dir / f"snapshot_{previous_year}.json"

        # Only create if snapshot doesn't exist and we have patterns
        has_patterns = (
            pattern_store.temporal or
            pattern_store.correlations or
            pattern_store.trajectories
        )

        if not historical_file.exists() and has_patterns:
            _ensure_patterns_dir(agent_id)

            # Save snapshot
            import json
            snapshot = {
                "version": pattern_store.version,
                "year": previous_year,
                "snapshot_date": today.strftime("%Y-%m-%d"),
                "temporal": pattern_store.temporal,
                "correlations": pattern_store.correlations,
                "trajectories": pattern_store.trajectories,
                # Exclude hypotheses - they're transient
            }
            with open(historical_file, "w") as f:
                json.dump(snapshot, f, indent=2)

            consolidation.logger.info({
                "event": "patterns_snapshot_created",
                "agent_id": agent_id,
                "year": previous_year,
                "temporal_count": len(pattern_store.temporal),
                "correlations_count": len(pattern_store.correlations),
                "trajectories_count": len(pattern_store.trajectories)
            })
