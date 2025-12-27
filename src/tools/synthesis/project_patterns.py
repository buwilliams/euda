"""
Project pattern analysis for behavioral synthesis.

Analyzes project and task completion data to extract behavioral patterns:
- Completion vs abandonment patterns
- Values actualization (do stated priorities match action)
- Work style patterns (time to complete, rollover frequency)
- Project type preferences
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from collections import defaultdict

# Import from worker tools
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
WORKER_DIR = DATA_DIR / "worker"
PROJECTS_DIR = WORKER_DIR / "state" / "projects"
ARCHIVE_DIR = WORKER_DIR / "state" / "archive"
TASKS_FILE = WORKER_DIR / "state" / "tasks" / "queue.json"


def _load_all_projects() -> list:
    """Load all projects (active and archived)."""
    projects = []

    # Active projects
    if PROJECTS_DIR.exists():
        for f in PROJECTS_DIR.glob("*.json"):
            if f.name.startswith("_"):
                continue
            try:
                with open(f, 'r') as file:
                    projects.append(json.load(file))
            except Exception:
                pass

    # Archived projects
    if ARCHIVE_DIR.exists():
        for f in ARCHIVE_DIR.glob("*.json"):
            try:
                with open(f, 'r') as file:
                    projects.append(json.load(file))
            except Exception:
                pass

    return projects


def _load_all_tasks() -> list:
    """Load all tasks."""
    if TASKS_FILE.exists():
        with open(TASKS_FILE, 'r') as f:
            data = json.load(f)
            return data.get("tasks", [])
    return []


def get_project_task_patterns(days: int = 90) -> str:
    """
    Analyze project/task data for behavioral patterns.

    Returns analysis of:
    - Completion patterns: What gets done vs abandoned
    - Abandonment patterns: When/why work stops
    - Work style: Time to complete, rollover frequency
    - Project type preferences

    Args:
        days: Look back period in days

    Returns:
        Formatted analysis for synthesis agent
    """
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    projects = _load_all_projects()
    tasks = _load_all_tasks()

    # Filter to relevant time period
    recent_projects = [
        p for p in projects
        if p.get("created", "") > cutoff or p.get("archived_at", "") > cutoff
    ]
    recent_tasks = [
        t for t in tasks
        if t.get("created", "") > cutoff
    ]

    # Analyze project completion
    project_stats = {
        "total": len(recent_projects),
        "active": 0,
        "completed": 0,
        "archived_abandoned": 0,
        "archived_paused": 0,
        "by_type": defaultdict(lambda: {"total": 0, "completed": 0}),
        "avg_completion_rate": 0,
    }

    total_completion_rate = 0
    completion_rate_count = 0

    for p in recent_projects:
        p_type = p.get("type", "goal")
        project_stats["by_type"][p_type]["total"] += 1

        if p.get("archived"):
            metadata = p.get("archive_metadata", {})
            outcome = metadata.get("outcome", "unknown")
            if outcome == "completed":
                project_stats["completed"] += 1
                project_stats["by_type"][p_type]["completed"] += 1
            elif outcome in ("abandoned", "paused"):
                if outcome == "abandoned":
                    project_stats["archived_abandoned"] += 1
                else:
                    project_stats["archived_paused"] += 1

            # Track completion rates
            rate = metadata.get("completion_rate", 0)
            if rate > 0:
                total_completion_rate += rate
                completion_rate_count += 1
        else:
            project_stats["active"] += 1

    if completion_rate_count > 0:
        project_stats["avg_completion_rate"] = total_completion_rate / completion_rate_count

    # Analyze task patterns
    task_stats = {
        "total": len(recent_tasks),
        "completed": 0,
        "archived": 0,
        "pending": 0,
        "avg_age_days": 0,
        "high_priority_completion_rate": 0,
        "rollover_count": 0,
        "by_type": defaultdict(lambda: {"total": 0, "completed": 0}),
    }

    total_age = 0
    high_priority_total = 0
    high_priority_completed = 0

    for t in recent_tasks:
        t_type = t.get("type", "general")
        task_stats["by_type"][t_type]["total"] += 1

        status = t.get("status", "pending")
        if status == "completed":
            task_stats["completed"] += 1
            task_stats["by_type"][t_type]["completed"] += 1
        elif status == "archived":
            task_stats["archived"] += 1
        else:
            task_stats["pending"] += 1

        # Track age
        try:
            created = datetime.fromisoformat(t["created"])
            age = (datetime.now() - created).days
            total_age += age
        except Exception:
            pass

        # Track high priority
        if t.get("priority") == "high":
            high_priority_total += 1
            if status == "completed":
                high_priority_completed += 1

        # Track rollovers
        rollover_count = t.get("rollover", {}).get("times_rolled", 0)
        task_stats["rollover_count"] += rollover_count

    if recent_tasks:
        task_stats["avg_age_days"] = total_age / len(recent_tasks)
    if high_priority_total > 0:
        task_stats["high_priority_completion_rate"] = high_priority_completed / high_priority_total

    # Build analysis output
    output = [
        f"## Project & Task Patterns (Last {days} Days)\n",
        f"### Project Overview",
        f"- Total projects: {project_stats['total']}",
        f"- Active: {project_stats['active']}",
        f"- Completed: {project_stats['completed']}",
        f"- Abandoned: {project_stats['archived_abandoned']}",
        f"- Paused: {project_stats['archived_paused']}",
        f"- Average task completion rate: {project_stats['avg_completion_rate']:.0%}",
        "",
        "### Project Types",
    ]

    for p_type, stats in project_stats["by_type"].items():
        rate = stats["completed"] / stats["total"] if stats["total"] > 0 else 0
        output.append(f"- {p_type}: {stats['completed']}/{stats['total']} completed ({rate:.0%})")

    output.extend([
        "",
        "### Task Overview",
        f"- Total tasks: {task_stats['total']}",
        f"- Completed: {task_stats['completed']}",
        f"- Archived: {task_stats['archived']}",
        f"- Pending: {task_stats['pending']}",
        f"- Average task age: {task_stats['avg_age_days']:.1f} days",
        f"- High priority completion rate: {task_stats['high_priority_completion_rate']:.0%}",
        f"- Total rollovers: {task_stats['rollover_count']}",
        "",
        "### Task Types",
    ])

    for t_type, stats in task_stats["by_type"].items():
        rate = stats["completed"] / stats["total"] if stats["total"] > 0 else 0
        output.append(f"- {t_type}: {stats['completed']}/{stats['total']} completed ({rate:.0%})")

    # Behavioral insights
    output.extend([
        "",
        "### Behavioral Signals",
    ])

    # Abandonment pattern
    if project_stats["archived_abandoned"] > project_stats["completed"]:
        output.append("- Pattern: More projects abandoned than completed - may indicate overcommitment or shifting priorities")
    elif project_stats["completed"] > 0:
        output.append("- Pattern: Generally completes what is started")

    # High priority behavior
    if task_stats["high_priority_completion_rate"] < 0.5 and high_priority_total > 3:
        output.append("- Pattern: High priority tasks often left incomplete - priority labeling may not reflect actual importance")
    elif task_stats["high_priority_completion_rate"] > 0.8:
        output.append("- Pattern: Reliably completes high priority work")

    # Rollover pattern
    avg_rollover = task_stats["rollover_count"] / task_stats["total"] if task_stats["total"] > 0 else 0
    if avg_rollover > 2:
        output.append(f"- Pattern: Frequent task rollovers ({avg_rollover:.1f} avg) - may overestimate daily capacity")

    return "\n".join(output)


def get_values_actualization_analysis() -> str:
    """
    Compare stated values (from profile) with project/task completion patterns.

    Looks for gaps between what user says matters and what actually gets done.

    Returns:
        Formatted analysis for synthesis agent
    """
    # Load profile values
    profile_file = DATA_DIR / "shared" / "state" / "profile" / "profile.current.md"
    profile_content = ""
    if profile_file.exists():
        profile_content = profile_file.read_text()

    # Extract values alignment from projects
    projects = _load_all_projects()
    tasks = _load_all_tasks()

    # Count completions by values alignment
    values_completion = defaultdict(lambda: {"total": 0, "completed": 0})

    for p in projects:
        values = p.get("values_alignment", [])
        is_completed = p.get("status") == "completed" or p.get("archive_metadata", {}).get("outcome") == "completed"

        for v in values:
            values_completion[v]["total"] += 1
            if is_completed:
                values_completion[v]["completed"] += 1

    # Analyze project types as proxy for values when explicit alignment not set
    type_to_value_proxy = {
        "learning": "growth",
        "habit": "discipline",
        "goal": "achievement",
        "maintenance": "stability",
    }

    for p in projects:
        p_type = p.get("type", "goal")
        proxy_value = type_to_value_proxy.get(p_type)
        if proxy_value and not p.get("values_alignment"):
            is_completed = p.get("status") == "completed" or p.get("archive_metadata", {}).get("outcome") == "completed"
            values_completion[f"implied:{proxy_value}"]["total"] += 1
            if is_completed:
                values_completion[f"implied:{proxy_value}"]["completed"] += 1

    # Build output
    output = [
        "## Values Actualization Analysis\n",
        "Comparing stated priorities with actual completion patterns:\n",
    ]

    if values_completion:
        output.append("### Completion by Value Alignment")
        for value, stats in sorted(values_completion.items(), key=lambda x: x[1]["total"], reverse=True):
            if stats["total"] > 0:
                rate = stats["completed"] / stats["total"]
                indicator = "+" if rate >= 0.5 else "-"
                output.append(f"{indicator} {value}: {stats['completed']}/{stats['total']} ({rate:.0%})")
    else:
        output.append("No values alignment data found in projects.")

    # Look for patterns
    output.extend([
        "",
        "### Insights",
    ])

    high_completion_values = [v for v, s in values_completion.items() if s["total"] >= 2 and s["completed"] / s["total"] >= 0.7]
    low_completion_values = [v for v, s in values_completion.items() if s["total"] >= 2 and s["completed"] / s["total"] < 0.3]

    if high_completion_values:
        output.append(f"- Consistently actualizes: {', '.join(high_completion_values)}")
    if low_completion_values:
        output.append(f"- Struggles to actualize: {', '.join(low_completion_values)}")

    if not high_completion_values and not low_completion_values:
        output.append("- Insufficient data for value actualization patterns")

    return "\n".join(output)


def get_abandonment_patterns() -> str:
    """
    Analyze patterns in abandoned projects and archived tasks.

    Returns:
        Formatted analysis of what tends to get abandoned and when
    """
    projects = _load_all_projects()
    tasks = _load_all_tasks()

    abandoned_projects = [
        p for p in projects
        if p.get("archive_metadata", {}).get("outcome") == "abandoned"
    ]

    archived_tasks = [
        t for t in tasks
        if t.get("status") == "archived"
    ]

    output = [
        "## Abandonment Pattern Analysis\n",
    ]

    # Project abandonment
    output.append(f"### Abandoned Projects ({len(abandoned_projects)})")

    if abandoned_projects:
        # Analyze by type
        by_type = defaultdict(int)
        total_age = 0
        total_completion_rate = 0

        for p in abandoned_projects:
            by_type[p.get("type", "goal")] += 1
            metadata = p.get("archive_metadata", {})
            total_age += metadata.get("age_days", 0)
            total_completion_rate += metadata.get("completion_rate", 0)

        avg_age = total_age / len(abandoned_projects)
        avg_rate = total_completion_rate / len(abandoned_projects)

        output.append(f"- Average age when abandoned: {avg_age:.0f} days")
        output.append(f"- Average completion rate: {avg_rate:.0%}")
        output.append("- By type:")
        for t, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            output.append(f"  - {t}: {count}")

        # Sample reasons
        reasons = [p.get("archive_metadata", {}).get("reason") for p in abandoned_projects if p.get("archive_metadata", {}).get("reason")]
        if reasons:
            output.append("- Reasons given:")
            for r in reasons[:5]:
                output.append(f"  - {r}")
    else:
        output.append("No abandoned projects found.")

    # Task archival
    output.append(f"\n### Archived Tasks ({len(archived_tasks)})")

    if archived_tasks:
        # Analyze by type and metadata
        by_outcome = defaultdict(int)
        total_age = 0
        total_rollover = 0

        for t in archived_tasks:
            metadata = t.get("archive_metadata", {})
            by_outcome[metadata.get("outcome", "unknown")] += 1
            total_age += metadata.get("age_days", 0)
            total_rollover += metadata.get("times_rolled", 0)

        if archived_tasks:
            avg_age = total_age / len(archived_tasks)
            avg_rollover = total_rollover / len(archived_tasks)

            output.append(f"- Average age when archived: {avg_age:.0f} days")
            output.append(f"- Average times rolled over: {avg_rollover:.1f}")
            output.append("- By outcome:")
            for o, count in sorted(by_outcome.items(), key=lambda x: x[1], reverse=True):
                output.append(f"  - {o}: {count}")
    else:
        output.append("No archived tasks found.")

    return "\n".join(output)


# Tool definitions for synthesis agent
PROJECT_PATTERN_TOOLS = [
    {
        "name": "get_project_task_patterns",
        "description": "Analyze project and task data for behavioral patterns. Returns completion rates, work style patterns, and behavioral signals.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Look back period in days (default: 90)"
                }
            }
        }
    },
    {
        "name": "get_values_actualization_analysis",
        "description": "Compare stated values with actual project completion patterns. Identifies gaps between what user says matters and what gets done.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_abandonment_patterns",
        "description": "Analyze patterns in abandoned projects and archived tasks. Identifies what types of work get abandoned and when.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

PROJECT_PATTERN_HANDLERS = {
    "get_project_task_patterns": get_project_task_patterns,
    "get_values_actualization_analysis": get_values_actualization_analysis,
    "get_abandonment_patterns": get_abandonment_patterns,
}
