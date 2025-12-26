"""
Health Assessment Tools - System health and gap detection

Tools for assessing system health, identifying configuration gaps,
and generating guidance for other agents. Used by the Evolution Agent
to proactively steer the system toward better user service.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
SIGNALS_DIR = SHARED_DIR / "signals"
SYNTHESIS_DIR = DATA_DIR / "synthesis"

# Ensure directories exist
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)


def assess_data_completeness() -> dict:
    """
    Check what user data exists vs what's missing.

    Returns:
        Dict with completeness status for each data category.
    """
    results = {
        "biographical": {"complete": False, "missing": []},
        "relationships": {"complete": False, "missing": []},
        "values": {"complete": False, "missing": []},
        "epistemic": {"complete": False, "missing": []},
        "behaviors": {"complete": False, "missing": []},
    }

    # Check biographical context
    bio_file = SYNTHESIS_DIR / "context" / "biographical.md"
    if bio_file.exists():
        content = bio_file.read_text().strip()
        # Check if it has actual content beyond template
        if len(content) > 100 and "Name:" in content:
            results["biographical"]["complete"] = True
        else:
            results["biographical"]["missing"] = ["name", "location", "birth_date"]
    else:
        results["biographical"]["missing"] = ["name", "location", "birth_date", "background"]

    # Check relationships
    rel_file = SYNTHESIS_DIR / "context" / "relationships.md"
    if rel_file.exists():
        content = rel_file.read_text().strip()
        if len(content) > 100:
            results["relationships"]["complete"] = True
        else:
            results["relationships"]["missing"] = ["family", "close_friends", "community"]
    else:
        results["relationships"]["missing"] = ["family", "close_friends", "community"]

    # Check values
    values_dir = SYNTHESIS_DIR / "values"
    if values_dir.exists():
        current = (values_dir / "current.values.md").exists()
        lifetime = (values_dir / "lifetime.values.md").exists()
        if current and lifetime:
            results["values"]["complete"] = True
        else:
            if not current:
                results["values"]["missing"].append("current_values")
            if not lifetime:
                results["values"]["missing"].append("lifetime_values")
    else:
        results["values"]["missing"] = ["current_values", "lifetime_values"]

    # Check epistemic
    epistemic_dir = SYNTHESIS_DIR / "epistemic"
    if epistemic_dir.exists():
        axioms = (epistemic_dir / "axioms.md").exists()
        if axioms:
            content = (epistemic_dir / "axioms.md").read_text()
            if len(content) > 100:
                results["epistemic"]["complete"] = True
    if not results["epistemic"]["complete"]:
        results["epistemic"]["missing"] = ["axioms", "mental_models"]

    # Check behaviors
    behaviors_dir = SYNTHESIS_DIR / "behaviors"
    if behaviors_dir.exists():
        patterns = (behaviors_dir / "patterns.md").exists()
        if patterns:
            content = (behaviors_dir / "patterns.md").read_text()
            if len(content) > 100:
                results["behaviors"]["complete"] = True
    if not results["behaviors"]["complete"]:
        results["behaviors"]["missing"] = ["patterns"]

    return results


def assess_configuration() -> dict:
    """
    Check what system configuration exists vs what's missing.

    Returns:
        Dict with configuration status.
    """
    results = {
        "energy_baseline": {"configured": False, "last_recorded": None},
        "attention_preferences": {"configured": False, "missing": []},
        "location": {"configured": False},
    }

    # Check energy signals
    energy_files = list(SIGNALS_DIR.glob("energy_*.json"))
    if energy_files:
        results["energy_baseline"]["configured"] = len(energy_files) >= 3  # Need a few samples
        # Get most recent
        most_recent = sorted(energy_files)[-1]
        results["energy_baseline"]["last_recorded"] = most_recent.stem.replace("energy_", "")

    # Check attention config
    attention_config = DATA_DIR / "attention" / "config"
    if attention_config.exists():
        config_files = list(attention_config.glob("*.json"))
        if config_files:
            results["attention_preferences"]["configured"] = True
        else:
            results["attention_preferences"]["missing"] = ["morning_time", "evening_time", "quiet_hours"]
    else:
        results["attention_preferences"]["missing"] = ["morning_time", "evening_time", "quiet_hours"]

    # Check if location is known (from biographical or elsewhere)
    bio_file = SYNTHESIS_DIR / "context" / "biographical.md"
    if bio_file.exists():
        content = bio_file.read_text()
        if "location" in content.lower() or "city" in content.lower():
            # Check if there's actual location data
            if any(term in content.lower() for term in ["smyrna", "atlanta", "georgia"]):
                results["location"]["configured"] = True

    return results


def assess_agent_activity() -> dict:
    """
    Check agent activity levels and health.

    Returns:
        Dict with activity status for each agent.
    """
    results = {}

    agents = ["ingestion", "summary", "synthesis", "world", "attention", "worker", "evolution"]

    for agent in agents:
        state_file = DATA_DIR / agent / "state" / "state.json"
        results[agent] = {
            "active": False,
            "last_work": None,
            "work_count": 0
        }

        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())

                # Check for recent activity
                last_work = state.get("last_work_time") or state.get("last_analysis") or state.get("updated")
                if last_work:
                    results[agent]["last_work"] = last_work
                    # Check if within last 24 hours
                    try:
                        last_dt = datetime.fromisoformat(last_work.replace("Z", "+00:00"))
                        if datetime.now() - last_dt.replace(tzinfo=None) < timedelta(hours=24):
                            results[agent]["active"] = True
                    except:
                        pass

                results[agent]["work_count"] = state.get("work_count", 0) or state.get("analysis_count", 0)
            except:
                pass

    # Special check for ingestion - check queue
    pending_dir = DATA_DIR / "ingestion" / "inbox" / "pending"
    if pending_dir.exists():
        pending_count = len([f for f in pending_dir.iterdir() if f.is_file() and not f.name.startswith('.')])
        results["ingestion"]["pending_files"] = pending_count
        if pending_count > 0:
            results["ingestion"]["active"] = True

    return results


def get_progress_metrics() -> dict:
    """
    Get progress metrics for user display.

    Returns:
        Dict with various progress indicators.
    """
    metrics = {
        "files_processed": 0,
        "log_entries": 0,
        "values_derived": 0,
        "patterns_identified": 0,
        "opportunities_found": 0,
    }

    # Count processed files
    processed_dir = DATA_DIR / "ingestion" / "inbox" / "processed"
    if processed_dir.exists():
        metrics["files_processed"] = len([f for f in processed_dir.iterdir() if f.is_file() and not f.name.startswith('.')])

    # Count log entries (rough estimate from lifelog)
    lifelog_dir = SHARED_DIR / "lifelog"
    if lifelog_dir.exists():
        for year_dir in lifelog_dir.iterdir():
            if year_dir.is_dir():
                metrics["log_entries"] += len(list(year_dir.glob("*.md")))

    # Count values
    values_dir = SYNTHESIS_DIR / "values"
    if values_dir.exists():
        for values_file in values_dir.glob("*.values.md"):
            content = values_file.read_text()
            # Count bullet points as rough value count
            metrics["values_derived"] += content.count("\n- ")

    # Count patterns
    patterns_file = SYNTHESIS_DIR / "behaviors" / "patterns.md"
    if patterns_file.exists():
        content = patterns_file.read_text()
        metrics["patterns_identified"] = content.count("## ") - 1  # Subtract header

    # Count opportunities
    opps_file = DATA_DIR / "world" / "opportunities" / "opportunities.json"
    if opps_file.exists():
        try:
            opps = json.loads(opps_file.read_text())
            metrics["opportunities_found"] = len(opps.get("opportunities", []))
        except:
            pass

    return metrics


def identify_gaps() -> list:
    """
    Identify all gaps that should be surfaced to the user.

    Returns:
        List of gap dictionaries with type, priority, and question.
    """
    gaps = []

    data = assess_data_completeness()
    config = assess_configuration()

    # High priority: Name (most personal)
    if "name" in data["biographical"].get("missing", []):
        gaps.append({
            "id": "biographical.name",
            "type": "missing_data",
            "category": "biographical",
            "field": "name",
            "priority": "high",
            "question": "Hey, I realized I don't know your name yet!",
            "context": "I'd love to address you personally instead of generically.",
            "action_prompt": "I'd like to get to know you better. What should I call you?"
        })

    # Medium priority: Location
    if not config["location"]["configured"]:
        gaps.append({
            "id": "biographical.location",
            "type": "missing_config",
            "category": "location",
            "field": "location",
            "priority": "medium",
            "question": "Quick thought - where are you based?",
            "context": "This helps me find relevant local events and opportunities for you.",
            "action_prompt": "I'm curious - where are you located? This helps me find relevant local opportunities."
        })

    # Low priority: Energy baseline
    if not config["energy_baseline"]["configured"]:
        gaps.append({
            "id": "config.energy_baseline",
            "type": "missing_config",
            "category": "energy",
            "field": "energy_baseline",
            "priority": "low",
            "question": "How's your energy today?",
            "context": "I'm learning your patterns to surface things at the right time.",
            "action_prompt": "I'd like to understand your energy patterns better. How are you feeling today - physically, mentally, emotionally?"
        })

    # Check if relationships empty
    if data["relationships"].get("missing"):
        gaps.append({
            "id": "biographical.relationships",
            "type": "missing_data",
            "category": "relationships",
            "field": "relationships",
            "priority": "low",
            "question": "I've been learning about you, but I don't know much about the people in your life yet.",
            "context": "Understanding your relationships helps me be more helpful.",
            "action_prompt": "Tell me about the important people in your life - family, close friends, community."
        })

    return gaps


def generate_agent_guidance(gaps: list) -> dict:
    """
    Generate guidance for other agents based on identified gaps.

    Args:
        gaps: List of identified gaps

    Returns:
        Guidance dict for each agent.
    """
    guidance = {
        "updated_at": datetime.now().isoformat(),
        "guidance": {}
    }

    gap_ids = [g["id"] for g in gaps]

    # Attention guidance
    attention_guidance = {}
    if "config.energy_baseline" in gap_ids:
        attention_guidance["ask_energy_in_morning"] = True
        attention_guidance["energy_reason"] = "No energy baseline established yet"
    guidance["guidance"]["attention"] = attention_guidance

    # World guidance
    world_guidance = {}
    if "biographical.location" in gap_ids:
        world_guidance["skip_location_opportunities"] = True
        world_guidance["location_reason"] = "User location unknown"
    guidance["guidance"]["world"] = world_guidance

    # Interaction guidance
    interaction_guidance = {}
    if "biographical.name" in gap_ids:
        interaction_guidance["learn_name_naturally"] = True
        interaction_guidance["name_reason"] = "User's name not yet known"
    guidance["guidance"]["interaction"] = interaction_guidance

    # Synthesis guidance
    synthesis_guidance = {}
    if any("biographical" in g for g in gap_ids):
        synthesis_guidance["prioritize_biographical"] = True
        synthesis_guidance["biographical_reason"] = "Context files need population"
    guidance["guidance"]["synthesis"] = synthesis_guidance

    return guidance


def write_gaps_signal(gaps: list) -> str:
    """
    Write gaps to signal file for Attention agent.

    Args:
        gaps: List of identified gaps

    Returns:
        Confirmation message.
    """
    signal = {
        "assessed_at": datetime.now().isoformat(),
        "gaps": gaps,
        "progress": get_progress_metrics()
    }

    signal_file = SIGNALS_DIR / "proactive_gaps.json"
    signal_file.write_text(json.dumps(signal, indent=2))

    return f"Wrote {len(gaps)} gaps to signal file"


def write_guidance_signal(guidance: dict) -> str:
    """
    Write guidance to signal file for other agents.

    Args:
        guidance: Guidance dict for agents

    Returns:
        Confirmation message.
    """
    signal_file = SIGNALS_DIR / "agent_guidance.json"
    signal_file.write_text(json.dumps(guidance, indent=2))

    return "Wrote agent guidance signal"


def run_health_assessment() -> str:
    """
    Run a full health assessment and write signals.

    Returns:
        Summary of assessment results.
    """
    # Gather all assessments
    data_status = assess_data_completeness()
    config_status = assess_configuration()
    activity_status = assess_agent_activity()
    progress = get_progress_metrics()
    gaps = identify_gaps()

    # Generate and write signals
    guidance = generate_agent_guidance(gaps)
    write_gaps_signal(gaps)
    write_guidance_signal(guidance)

    # Build summary
    summary = "# System Health Assessment\n\n"

    summary += "## Data Completeness\n"
    for category, status in data_status.items():
        icon = "complete" if status["complete"] else "incomplete"
        summary += f"- **{category}**: {icon}\n"
        if status.get("missing"):
            summary += f"  Missing: {', '.join(status['missing'])}\n"

    summary += "\n## Configuration\n"
    for item, status in config_status.items():
        configured = status.get("configured", False)
        summary += f"- **{item}**: {'configured' if configured else 'not configured'}\n"

    summary += "\n## Agent Activity (last 24h)\n"
    for agent, status in activity_status.items():
        active = "active" if status["active"] else "inactive"
        summary += f"- **{agent}**: {active}"
        if status.get("pending_files"):
            summary += f" ({status['pending_files']} files pending)"
        summary += "\n"

    summary += "\n## Progress\n"
    summary += f"- Files processed: {progress['files_processed']}\n"
    summary += f"- Log entries: {progress['log_entries']}\n"
    summary += f"- Values derived: {progress['values_derived']}\n"
    summary += f"- Patterns identified: {progress['patterns_identified']}\n"

    summary += f"\n## Gaps Identified: {len(gaps)}\n"
    for gap in gaps:
        summary += f"- [{gap['priority']}] {gap['question']}\n"

    return summary


# Tool definitions
HEALTH_TOOLS = [
    {
        "name": "assess_data_completeness",
        "description": "Check what user data exists vs what's missing (biographical, relationships, values, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "assess_configuration",
        "description": "Check system configuration status (energy baseline, preferences, location)",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "assess_agent_activity",
        "description": "Check agent activity levels and health over last 24 hours",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_progress_metrics",
        "description": "Get progress metrics to show the user (files processed, values derived, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "identify_gaps",
        "description": "Identify all gaps that should be surfaced to the user as proactive questions",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "run_health_assessment",
        "description": "Run a full health assessment, identify gaps, and write signals for other agents",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

HEALTH_HANDLERS = {
    "assess_data_completeness": assess_data_completeness,
    "assess_configuration": assess_configuration,
    "assess_agent_activity": assess_agent_activity,
    "get_progress_metrics": get_progress_metrics,
    "identify_gaps": identify_gaps,
    "run_health_assessment": run_health_assessment,
}
