"""
Task management tools for daily and project-based tasks.

Tasks are individual actionable items that can be standalone (ad-hoc) or
associated with a project. The Worker Agent processes tasks based on
delegation rules.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
TASKS_DIR = DATA_DIR / "tasks"
QUEUE_FILE = TASKS_DIR / "queue.json"
DAILY_DIR = TASKS_DIR / "daily"
RESULTS_DIR = TASKS_DIR / "results"
LEARNING_DIR = TASKS_DIR / "learning"
CONFIG_DIR = TASKS_DIR / "config"

# Ensure directories exist
DAILY_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LEARNING_DIR.mkdir(parents=True, exist_ok=True)


def _generate_task_id() -> str:
    """Generate a unique task ID."""
    return f"task-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"


def _generate_result_id() -> str:
    """Generate a unique result ID."""
    return f"result-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"


def _load_queue() -> dict:
    """Load the task queue."""
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE, 'r') as f:
            return json.load(f)
    return {"tasks": []}


def _save_queue(queue: dict):
    """Save the task queue."""
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=2)


def _load_delegation_config() -> dict:
    """Load delegation configuration."""
    config_file = CONFIG_DIR / "delegation.json"
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    return {
        "auto_execute": {"research": True, "fetch_info": True},
        "require_approval": {"email_send": True, "calendar_create": True},
        "user_only": {"physical_activity": True, "creative_work": True, "learning_execution": True}
    }


def _load_rollover_config() -> dict:
    """Load rollover configuration."""
    config_file = CONFIG_DIR / "rollover.json"
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    return {
        "strategies": {"high_priority": "always_migrate", "max_rollover_count": 3}
    }


def determine_delegation(task_type: str, is_learning: bool = False) -> dict:
    """
    Determine how a task should be delegated based on rules.

    Args:
        task_type: Type of task (research, email_send, physical_activity, etc.)
        is_learning: Whether this is a learning-focused task

    Returns:
        Delegation dict with strategy and flags
    """
    config = _load_delegation_config()

    # Learning tasks get special handling
    if is_learning:
        return {
            "strategy": "prepare_materials",
            "requires_approval": False,
            "learning_task": True,
            "rationale": "Learning task - will prepare materials for user"
        }

    # User-only tasks
    if task_type in config.get("user_only", {}):
        return {
            "strategy": "user_only",
            "requires_approval": False,
            "learning_task": False,
            "rationale": f"{task_type} requires user action"
        }

    # High-stakes tasks requiring approval
    if task_type in config.get("require_approval", {}):
        return {
            "strategy": "agent_with_approval",
            "requires_approval": True,
            "learning_task": False,
            "rationale": f"{task_type} requires user approval before execution"
        }

    # Auto-execute tasks
    if task_type in config.get("auto_execute", {}):
        return {
            "strategy": "agent_autonomous",
            "requires_approval": False,
            "learning_task": False,
            "rationale": f"{task_type} can be completed autonomously"
        }

    # Default: require approval to be safe
    return {
        "strategy": "agent_with_approval",
        "requires_approval": True,
        "learning_task": False,
        "rationale": "Default: requires approval"
    }


def create_task(
    description: str,
    task_type: str = "general",
    project_id: Optional[str] = None,
    priority: str = "normal",
    due_date: Optional[str] = None,
    time_estimate_minutes: Optional[int] = None,
    energy_level: str = "medium",
    best_window: str = "any",
    source_agent: str = "user",
    source_context: str = "",
    is_learning: bool = False
) -> str:
    """
    Create a new task.

    Args:
        description: What needs to be done
        task_type: Type of task (research, email_send, reminder, etc.)
        project_id: Optional project to associate with
        priority: high, normal, or low
        due_date: When it should be done (ISO format)
        time_estimate_minutes: Estimated time to complete
        energy_level: Required energy - low, medium, high
        best_window: Best time - morning, afternoon, evening, any
        source_agent: Which agent created this
        source_context: Why it was created
        is_learning: Whether this is a learning task

    Returns:
        Success message with task ID
    """
    task_id = _generate_task_id()
    now = datetime.now().isoformat()

    # Determine delegation strategy
    delegation = determine_delegation(task_type, is_learning)

    task = {
        "id": task_id,
        "created": now,
        "description": description,
        "type": task_type,
        "status": "pending",
        "priority": priority,
        "source": {
            "agent": source_agent,
            "context": source_context
        },
        "project_id": project_id,
        "delegation": delegation,
        "scheduling": {
            "due_date": due_date,
            "scheduled_for": None,
            "time_estimate_minutes": time_estimate_minutes,
            "energy_level": energy_level,
            "best_window": best_window
        },
        "rollover": {
            "original_date": None,
            "times_rolled": 0,
            "rollover_decision": None
        },
        "assigned_at": None,
        "completed_at": None,
        "result": None,
        "result_id": None
    }

    # Add to queue
    queue = _load_queue()
    queue["tasks"].append(task)
    _save_queue(queue)

    # Update project task count if associated
    if project_id:
        from .project import increment_task_count
        increment_task_count(project_id)

    strategy_msg = f" ({delegation['strategy']})" if delegation else ""
    return f"Created task: '{description}'{strategy_msg} (ID: {task_id})"


def create_learning_task(
    description: str,
    project_id: Optional[str] = None,
    learning_objectives: Optional[list] = None,
    preferred_format: str = "mixed",
    priority: str = "normal",
    due_date: Optional[str] = None
) -> str:
    """
    Create a learning-focused task where the agent prepares materials.

    Args:
        description: What the user wants to learn
        project_id: Optional learning project
        learning_objectives: Specific goals for this learning session
        preferred_format: video, reading, interactive, mixed
        priority: high, normal, or low
        due_date: When to have materials ready

    Returns:
        Success message
    """
    task_id = _generate_task_id()
    now = datetime.now().isoformat()

    task = {
        "id": task_id,
        "created": now,
        "description": description,
        "type": "learning",
        "status": "pending",
        "priority": priority,
        "source": {
            "agent": "user",
            "context": "User learning request"
        },
        "project_id": project_id,
        "delegation": {
            "strategy": "prepare_materials",
            "requires_approval": False,
            "learning_task": True,
            "rationale": "Learning task - will curate and prepare materials"
        },
        "learning": {
            "objectives": learning_objectives or [],
            "preferred_format": preferred_format,
            "materials_ready": False,
            "material_id": None
        },
        "scheduling": {
            "due_date": due_date,
            "scheduled_for": None,
            "time_estimate_minutes": None,
            "energy_level": "high",
            "best_window": "any"
        },
        "rollover": {
            "original_date": None,
            "times_rolled": 0
        },
        "assigned_at": None,
        "completed_at": None,
        "result": None,
        "result_id": None
    }

    queue = _load_queue()
    queue["tasks"].append(task)
    _save_queue(queue)

    if project_id:
        from .project import increment_task_count
        increment_task_count(project_id)

    return f"Created learning task: '{description}' - materials will be prepared (ID: {task_id})"


def get_tasks(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50
) -> str:
    """
    Get tasks with optional filters.

    Args:
        status: Filter by status (pending, in_progress, completed, etc.)
        project_id: Filter by project
        due_date: Filter by due date
        priority: Filter by priority
        limit: Maximum number of tasks to return

    Returns:
        Formatted list of tasks
    """
    queue = _load_queue()
    tasks = queue["tasks"]

    # Apply filters
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if project_id:
        tasks = [t for t in tasks if t.get("project_id") == project_id]
    if due_date:
        tasks = [t for t in tasks if t.get("scheduling", {}).get("due_date") == due_date]
    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]

    # Sort by priority then due date
    priority_order = {"high": 0, "normal": 1, "low": 2}
    tasks.sort(key=lambda t: (
        priority_order.get(t.get("priority", "normal"), 1),
        t.get("scheduling", {}).get("due_date") or "9999-12-31"
    ))

    tasks = tasks[:limit]

    if not tasks:
        return "No tasks found matching criteria."

    output = [f"## Tasks ({len(tasks)})\n"]
    for t in tasks:
        priority_str = f" [{t['priority'].upper()}]" if t.get("priority") == "high" else ""
        due = t.get("scheduling", {}).get("due_date")
        due_str = f" (due: {due})" if due else ""
        status_icon = {"pending": " ", "in_progress": ">", "completed": "x", "awaiting_approval": "?"}
        icon = status_icon.get(t["status"], " ")

        output.append(f"- [{icon}] {t['description']}{priority_str}{due_str}")
        if t.get("project_id"):
            output.append(f"    Project: {t['project_id']}")

    return "\n".join(output)


def get_tasks_data(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50
) -> list:
    """
    Get tasks as raw data for API consumption.

    Returns:
        List of task dictionaries
    """
    queue = _load_queue()
    tasks = queue["tasks"]

    # Apply filters
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if project_id:
        tasks = [t for t in tasks if t.get("project_id") == project_id]
    if due_date:
        tasks = [t for t in tasks if t.get("scheduling", {}).get("due_date") == due_date]
    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]

    # Sort by priority then due date
    priority_order = {"high": 0, "normal": 1, "low": 2}
    tasks.sort(key=lambda t: (
        priority_order.get(t.get("priority", "normal"), 1),
        t.get("scheduling", {}).get("due_date") or "9999-12-31"
    ))

    return tasks[:limit]


def get_task(task_id: str) -> str:
    """
    Get details of a specific task.

    Args:
        task_id: The task ID

    Returns:
        Formatted task details
    """
    queue = _load_queue()

    for task in queue["tasks"]:
        if task["id"] == task_id:
            output = [
                f"# Task: {task['description']}",
                f"**Status:** {task['status']} | **Priority:** {task['priority']} | **Type:** {task['type']}",
                f"**Created:** {task['created'][:10]}",
            ]

            if task.get("project_id"):
                output.append(f"**Project:** {task['project_id']}")

            delegation = task.get("delegation", {})
            output.append(f"\n**Delegation:** {delegation.get('strategy', 'unknown')}")
            output.append(f"*{delegation.get('rationale', '')}*")

            scheduling = task.get("scheduling", {})
            if scheduling.get("due_date"):
                output.append(f"\n**Due:** {scheduling['due_date']}")
            if scheduling.get("time_estimate_minutes"):
                output.append(f"**Time estimate:** {scheduling['time_estimate_minutes']} min")

            if task.get("result_id"):
                output.append(f"\n**Result:** {task['result_id']}")

            output.append(f"\n*ID: {task['id']}*")
            return "\n".join(output)

    return f"Task not found: {task_id}"


def get_daily_view(date: Optional[str] = None) -> str:
    """
    Get the daily task view showing scheduled and ad-hoc tasks.

    Args:
        date: Date to get view for (ISO format, defaults to today)

    Returns:
        Formatted daily view
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # Load daily file if exists
    daily_file = DAILY_DIR / f"{date}.json"
    daily_data = {"date": date, "tasks": [], "ad_hoc_tasks": []}

    if daily_file.exists():
        with open(daily_file, 'r') as f:
            daily_data = json.load(f)

    # Get tasks due today from queue
    queue = _load_queue()
    due_today = [
        t for t in queue["tasks"]
        if t.get("scheduling", {}).get("due_date") == date
        and t["status"] not in ["completed", "archived"]
    ]

    # Get pending tasks without due date (could be done today)
    pending_no_date = [
        t for t in queue["tasks"]
        if not t.get("scheduling", {}).get("due_date")
        and t["status"] == "pending"
        and t["priority"] in ["high", "normal"]
    ][:5]  # Limit suggestions

    output = [f"# Tasks for {date}\n"]

    if due_today:
        output.append("## Due Today")
        for t in due_today:
            priority_str = f" [{t['priority'].upper()}]" if t.get("priority") == "high" else ""
            status_icon = {"pending": " ", "in_progress": ">", "completed": "x"}
            icon = status_icon.get(t["status"], " ")
            output.append(f"- [{icon}] {t['description']}{priority_str}")

    if daily_data.get("ad_hoc_tasks"):
        output.append("\n## Quick Tasks")
        for t in daily_data["ad_hoc_tasks"]:
            icon = "x" if t.get("status") == "completed" else " "
            output.append(f"- [{icon}] {t['description']}")

    if pending_no_date:
        output.append("\n## Could Do Today")
        for t in pending_no_date:
            output.append(f"- {t['description']}")

    if len(output) == 1:
        output.append("No tasks scheduled for today. Enjoy the freedom!")

    return "\n".join(output)


def add_quick_task(description: str, date: Optional[str] = None) -> str:
    """
    Add a quick ad-hoc task for today.

    Args:
        description: What needs to be done
        date: Date to add to (defaults to today)

    Returns:
        Success message
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    daily_file = DAILY_DIR / f"{date}.json"

    if daily_file.exists():
        with open(daily_file, 'r') as f:
            daily_data = json.load(f)
    else:
        daily_data = {
            "date": date,
            "morning_review_done": False,
            "evening_review_done": False,
            "tasks": [],
            "ad_hoc_tasks": [],
            "notes": ""
        }

    task_id = f"adhoc-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    daily_data["ad_hoc_tasks"].append({
        "id": task_id,
        "description": description,
        "created": datetime.now().isoformat(),
        "status": "pending",
        "quick": True
    })

    with open(daily_file, 'w') as f:
        json.dump(daily_data, f, indent=2)

    return f"Added quick task: '{description}'"


def complete_quick_task(task_id: str, date: Optional[str] = None) -> str:
    """
    Complete a quick ad-hoc task.

    Args:
        task_id: The ad-hoc task ID
        date: Date of the task

    Returns:
        Success message
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    daily_file = DAILY_DIR / f"{date}.json"

    if not daily_file.exists():
        return f"No daily file for {date}"

    with open(daily_file, 'r') as f:
        daily_data = json.load(f)

    for task in daily_data.get("ad_hoc_tasks", []):
        if task["id"] == task_id:
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()

            with open(daily_file, 'w') as f:
                json.dump(daily_data, f, indent=2)

            return "Completed task"

    return f"Task not found: {task_id}"


def schedule_task(task_id: str, date: str, window: str = "any") -> str:
    """
    Schedule a task for a specific day/time window.

    Args:
        task_id: The task ID
        date: Date to schedule for (ISO format)
        window: Time window - morning, afternoon, evening, any

    Returns:
        Success message
    """
    queue = _load_queue()

    for task in queue["tasks"]:
        if task["id"] == task_id:
            if "scheduling" not in task:
                task["scheduling"] = {}

            task["scheduling"]["scheduled_for"] = date
            task["scheduling"]["best_window"] = window

            _save_queue(queue)
            return f"Scheduled task for {date} ({window})"

    return f"Task not found: {task_id}"


def update_task_status(task_id: str, status: str) -> str:
    """
    Update task status.

    Args:
        task_id: The task ID
        status: New status (pending, in_progress, completed, etc.)

    Returns:
        Success message
    """
    queue = _load_queue()

    for task in queue["tasks"]:
        if task["id"] == task_id:
            task["status"] = status

            if status == "in_progress":
                task["assigned_at"] = datetime.now().isoformat()
            elif status == "completed":
                task["completed_at"] = datetime.now().isoformat()

                # Update project completed count
                if task.get("project_id"):
                    from .project import increment_task_count
                    increment_task_count(task["project_id"], completed=True)

            _save_queue(queue)
            return f"Updated task status to {status}"

    return f"Task not found: {task_id}"


def delete_task(task_id: str) -> str:
    """
    Delete a task from the queue.

    Args:
        task_id: The task ID to delete

    Returns:
        Success or error message
    """
    queue = _load_queue()

    for i, task in enumerate(queue["tasks"]):
        if task["id"] == task_id:
            description = task["description"]
            queue["tasks"].pop(i)
            _save_queue(queue)
            return f"Deleted task: {description}"

    return f"Task not found: {task_id}"


def delete_tasks_by_description(description_contains: str) -> str:
    """
    Delete all tasks whose description contains the given text.

    Args:
        description_contains: Text to match in task descriptions

    Returns:
        Success message with count of deleted tasks
    """
    queue = _load_queue()
    original_count = len(queue["tasks"])

    # Filter out matching tasks
    queue["tasks"] = [
        t for t in queue["tasks"]
        if description_contains.lower() not in t["description"].lower()
    ]

    deleted_count = original_count - len(queue["tasks"])

    if deleted_count > 0:
        _save_queue(queue)
        return f"Deleted {deleted_count} task(s) matching '{description_contains}'"

    return f"No tasks found matching '{description_contains}'"


def store_result(
    task_id: str,
    summary: str,
    content: dict,
    recommendations: Optional[str] = None
) -> str:
    """
    Store the result of a completed task.

    Args:
        task_id: The task ID this result is for
        summary: Brief summary of what was accomplished
        content: Structured content of the result
        recommendations: Optional next steps

    Returns:
        Success message with result ID
    """
    result_id = _generate_result_id()
    now = datetime.now()

    # Find the task
    queue = _load_queue()
    task = None
    for t in queue["tasks"]:
        if t["id"] == task_id:
            task = t
            break

    if not task:
        return f"Task not found: {task_id}"

    result = {
        "id": result_id,
        "created": now.isoformat(),
        "task_id": task_id,
        "project_id": task.get("project_id"),
        "type": task.get("type", "general"),
        "summary": summary,
        "content": content,
        "recommendations": recommendations,
        "surfaced_to_user": False,
        "surfaced_at": None,
        "user_feedback": None
    }

    # Create results directory for this month
    year_month = now.strftime("%Y/%m")
    result_dir = RESULTS_DIR / year_month
    result_dir.mkdir(parents=True, exist_ok=True)

    result_file = result_dir / f"{result_id}.json"
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)

    # Update task with result reference
    task["result_id"] = result_id
    task["result"] = summary
    _save_queue(queue)

    return f"Stored result: {summary} (ID: {result_id})"


def get_result(result_id: str) -> str:
    """
    Get a specific result.

    Args:
        result_id: The result ID

    Returns:
        Formatted result details
    """
    # Search in results directory
    for year_dir in RESULTS_DIR.iterdir():
        if year_dir.is_dir():
            for month_dir in year_dir.iterdir():
                if month_dir.is_dir():
                    result_file = month_dir / f"{result_id}.json"
                    if result_file.exists():
                        with open(result_file, 'r') as f:
                            result = json.load(f)

                        output = [
                            f"# Result: {result['summary']}",
                            f"**Task:** {result['task_id']}",
                            f"**Created:** {result['created'][:10]}",
                        ]

                        if result.get("project_id"):
                            output.append(f"**Project:** {result['project_id']}")

                        output.append(f"\n## Content\n```json\n{json.dumps(result['content'], indent=2)}\n```")

                        if result.get("recommendations"):
                            output.append(f"\n## Recommendations\n{result['recommendations']}")

                        return "\n".join(output)

    return f"Result not found: {result_id}"


def get_recent_results(project_id: Optional[str] = None, limit: int = 10) -> str:
    """
    Get recent results, optionally filtered by project.

    Args:
        project_id: Filter by project
        limit: Maximum results to return

    Returns:
        Formatted list of results
    """
    results = []

    # Scan results directory (most recent first)
    year_dirs = sorted(RESULTS_DIR.iterdir(), reverse=True) if RESULTS_DIR.exists() else []

    for year_dir in year_dirs:
        if not year_dir.is_dir():
            continue
        month_dirs = sorted(year_dir.iterdir(), reverse=True)

        for month_dir in month_dirs:
            if not month_dir.is_dir():
                continue
            result_files = sorted(month_dir.glob("*.json"), reverse=True)

            for result_file in result_files:
                with open(result_file, 'r') as f:
                    result = json.load(f)

                if project_id and result.get("project_id") != project_id:
                    continue

                results.append(result)

                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    if not results:
        return "No results found."

    output = ["## Recent Results\n"]
    for r in results:
        date = r["created"][:10]
        output.append(f"### {r['summary']} ({date})")
        if r.get("project_id"):
            output.append(f"**Project:** {r['project_id']}")
        output.append(f"**Result ID:** {r['id']}")

        # Include the content details
        if r.get("content"):
            content = r["content"]
            if isinstance(content, dict):
                output.append("\n**Details:**")
                output.append(json.dumps(content, indent=2))
            else:
                output.append(f"\n**Details:** {content}")

        # Include recommendations if present
        if r.get("recommendations"):
            output.append(f"\n**Next Steps:** {r['recommendations']}")

        output.append("")  # Blank line between results

    return "\n".join(output)


def process_rollover(date: Optional[str] = None) -> str:
    """
    Process rollover for incomplete tasks from a given date.
    Called by Attention Agent in evening.

    Args:
        date: Date to process (defaults to today)

    Returns:
        Summary of rollover decisions
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    config = _load_rollover_config()
    max_rolls = config.get("strategies", {}).get("max_rollover_count", 3)

    queue = _load_queue()
    tomorrow = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    decisions = []

    for task in queue["tasks"]:
        if task["status"] not in ["pending", "in_progress"]:
            continue

        due_date = task.get("scheduling", {}).get("due_date")
        if due_date and due_date <= date:
            rollover = task.get("rollover", {"times_rolled": 0})
            times_rolled = rollover.get("times_rolled", 0)

            # Decision logic
            if task["priority"] == "high":
                # Always migrate high priority
                task["scheduling"]["due_date"] = tomorrow
                rollover["times_rolled"] = times_rolled + 1
                if not rollover.get("original_date"):
                    rollover["original_date"] = due_date
                rollover["rollover_decision"] = "migrated_high_priority"
                decisions.append(f"Migrated (high priority): {task['description']}")

            elif times_rolled >= max_rolls:
                # Stale - needs user review
                task["status"] = "stale"
                rollover["rollover_decision"] = "marked_stale"
                decisions.append(f"Marked stale ({times_rolled}x rolled): {task['description']}")

            elif task["priority"] == "low":
                # Archive low priority stale tasks
                task["status"] = "archived"
                rollover["rollover_decision"] = "archived_low_priority"
                decisions.append(f"Archived (low priority): {task['description']}")

            else:
                # Default: migrate
                task["scheduling"]["due_date"] = tomorrow
                rollover["times_rolled"] = times_rolled + 1
                if not rollover.get("original_date"):
                    rollover["original_date"] = due_date
                rollover["rollover_decision"] = "migrated"
                decisions.append(f"Migrated: {task['description']}")

            task["rollover"] = rollover

    _save_queue(queue)

    if not decisions:
        return "No tasks needed rollover processing."

    return f"## Rollover Decisions\n\n" + "\n".join(f"- {d}" for d in decisions)


def get_overdue_tasks() -> list:
    """
    Get list of overdue tasks.

    Returns:
        List of overdue task dicts
    """
    today = datetime.now().strftime("%Y-%m-%d")
    queue = _load_queue()

    overdue = []
    for task in queue["tasks"]:
        if task["status"] in ["completed", "archived"]:
            continue

        due_date = task.get("scheduling", {}).get("due_date")
        if due_date and due_date < today:
            overdue.append(task)

    return overdue


def get_pending_tasks_for_worker() -> list:
    """
    Get pending tasks that the Worker Agent should process.

    Returns:
        List of tasks ready for processing
    """
    queue = _load_queue()

    pending = []
    for task in queue["tasks"]:
        if task["status"] != "pending":
            continue

        delegation = task.get("delegation", {})

        # Skip user-only tasks
        if delegation.get("strategy") == "user_only":
            continue

        pending.append(task)

    # Sort by priority
    priority_order = {"high": 0, "normal": 1, "low": 2}
    pending.sort(key=lambda t: priority_order.get(t.get("priority", "normal"), 1))

    return pending


# Tool definitions for agents
TASK_TOOLS = [
    {
        "name": "create_task",
        "description": "Create a new task. Use this when the user wants to add something to their task list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "What needs to be done"
                },
                "task_type": {
                    "type": "string",
                    "enum": ["general", "research", "email_send", "calendar_create", "reminder", "physical_activity", "creative_work", "learning"],
                    "description": "Type of task (affects delegation)"
                },
                "project_id": {
                    "type": "string",
                    "description": "Optional project to associate with"
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "normal", "low"],
                    "description": "Priority level"
                },
                "due_date": {
                    "type": "string",
                    "description": "When it should be done (YYYY-MM-DD)"
                }
            },
            "required": ["description"]
        }
    },
    {
        "name": "create_learning_task",
        "description": "Create a learning task where the agent will prepare materials for the user to study.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "What the user wants to learn"
                },
                "project_id": {
                    "type": "string",
                    "description": "Learning project to associate with"
                },
                "learning_objectives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific learning goals"
                },
                "preferred_format": {
                    "type": "string",
                    "enum": ["video", "reading", "interactive", "mixed"],
                    "description": "Preferred learning format"
                }
            },
            "required": ["description"]
        }
    },
    {
        "name": "get_tasks",
        "description": "Get tasks with optional filters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "stale"]
                },
                "project_id": {"type": "string"},
                "priority": {
                    "type": "string",
                    "enum": ["high", "normal", "low"]
                },
                "limit": {"type": "integer"}
            }
        }
    },
    {
        "name": "get_daily_view",
        "description": "Get today's task view showing due tasks and quick tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to view (YYYY-MM-DD, defaults to today)"
                }
            }
        }
    },
    {
        "name": "add_quick_task",
        "description": "Add a quick ad-hoc task for today. Use for simple one-off items.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "What needs to be done"
                }
            },
            "required": ["description"]
        }
    },
    {
        "name": "get_recent_results",
        "description": "Get recent completed work results. Shows what the agent has accomplished.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Filter by project"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)"
                }
            }
        }
    },
    {
        "name": "update_task_status",
        "description": "Update a task's status. Use to mark tasks as completed, in progress, or pending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed"],
                    "description": "New status"
                }
            },
            "required": ["task_id", "status"]
        }
    },
    {
        "name": "delete_task",
        "description": "Delete a task by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to delete"
                }
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "delete_tasks_by_description",
        "description": "Delete all tasks whose description contains the given text. Use to clean up duplicate or test tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description_contains": {
                    "type": "string",
                    "description": "Text to match in task descriptions (case-insensitive)"
                }
            },
            "required": ["description_contains"]
        }
    }
]

TASK_HANDLERS = {
    "create_task": create_task,
    "create_learning_task": create_learning_task,
    "get_tasks": get_tasks,
    "get_daily_view": get_daily_view,
    "add_quick_task": add_quick_task,
    "get_recent_results": get_recent_results,
    "update_task_status": update_task_status,
    "delete_task": delete_task,
    "delete_tasks_by_description": delete_tasks_by_description,
}
