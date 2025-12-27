"""
Worker Tools - Task and action management for the Worker Agent.

Handles:
- Task queue management (via task.py for the new project-based system)
- Pending action management (create, approve, reject, execute)
- Action history tracking
- Delegation decisions (what agent does vs what user does)
- Results storage
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Import new task and project systems
from .task import (
    create_task as new_create_task,
    create_learning_task,
    get_tasks as new_get_tasks,
    get_task as new_get_task,
    get_daily_view,
    add_quick_task,
    update_task_status as new_update_task_status,
    store_result,
    get_recent_results,
    get_pending_tasks_for_worker,
    process_rollover,
    determine_delegation,
    TASK_TOOLS, TASK_HANDLERS,
    AUTONOMOUS_TASK_TOOLS, AUTONOMOUS_TASK_HANDLERS
)
from .project import (
    create_project,
    get_projects,
    get_project,
    update_project,
    add_milestone,
    archive_project,
    get_projects_with_deadlines,
    PROJECT_TOOLS, PROJECT_HANDLERS
)

# Data paths - Worker agent directory
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
WORKER_DIR = DATA_DIR / "worker"
TASKS_FILE = WORKER_DIR / "state" / "tasks" / "queue.json"
PENDING_FILE = WORKER_DIR / "state" / "actions" / "pending.json"
COMPLETED_FILE = WORKER_DIR / "state" / "actions" / "completed.json"
CONFIG_FILE = WORKER_DIR / "config" / "integrations.json"


def _load_json(path: Path) -> dict:
    """Load JSON file."""
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def _save_json(path: Path, data: dict):
    """Save JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def _generate_id(prefix: str) -> str:
    """Generate a unique ID."""
    return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"


# ============== Task Management ==============

def create_task(
    description: str,
    task_type: str,
    source: str = "user",
    priority: str = "normal",
    source_context: str = "",
    deadline: str = None
) -> str:
    """
    Create a new task in the queue.

    Args:
        description: What needs to be done
        task_type: Type of task (email, calendar, research, reminder)
        source: Who created it (interaction, attention, user)
        priority: Priority level (high, normal, low)
        source_context: Additional context from the source
        deadline: Optional deadline (ISO format)

    Returns:
        Confirmation with task ID
    """
    data = _load_json(TASKS_FILE)
    if "tasks" not in data:
        data["tasks"] = []

    task_id = _generate_id("task")
    task = {
        "id": task_id,
        "created": datetime.now().isoformat(),
        "description": description,
        "type": task_type,
        "source": source,
        "source_context": source_context,
        "priority": priority,
        "deadline": deadline,
        "status": "pending",
        "assigned_at": None,
        "completed_at": None,
        "result": None
    }

    data["tasks"].append(task)
    _save_json(TASKS_FILE, data)

    return f"Task created: {task_id}\nType: {task_type}\nDescription: {description}"


def get_tasks(status: str = "", task_type: str = "", limit: int = 20) -> str:
    """
    Get tasks from the queue.

    Args:
        status: Filter by status (pending, in_progress, awaiting_approval, completed)
        task_type: Filter by type (email, calendar, research, reminder)
        limit: Maximum number of tasks to return

    Returns:
        Formatted list of tasks
    """
    data = _load_json(TASKS_FILE)
    tasks = data.get("tasks", [])

    # Filter
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if task_type:
        tasks = [t for t in tasks if t["type"] == task_type]

    # Sort by priority and creation time
    priority_order = {"high": 0, "normal": 1, "low": 2}
    tasks.sort(key=lambda t: (priority_order.get(t["priority"], 1), t["created"]))

    # Limit
    tasks = tasks[:limit]

    if not tasks:
        return "No tasks found matching criteria."

    lines = [f"Tasks ({len(tasks)}):"]
    for task in tasks:
        priority_marker = "!" if task["priority"] == "high" else ""
        lines.append(f"\n[{task['id']}] {priority_marker}{task['status'].upper()}")
        lines.append(f"  Type: {task['type']}")
        lines.append(f"  Description: {task['description']}")
        lines.append(f"  Source: {task['source']}")
        if task["deadline"]:
            lines.append(f"  Deadline: {task['deadline']}")

    return "\n".join(lines)


def get_task(task_id: str) -> str:
    """
    Get details of a specific task.

    Args:
        task_id: The task ID

    Returns:
        Task details or error message
    """
    data = _load_json(TASKS_FILE)
    tasks = data.get("tasks", [])

    for task in tasks:
        if task["id"] == task_id:
            return json.dumps(task, indent=2)

    return f"Task not found: {task_id}"


def update_task_status(task_id: str, status: str, result: str = None) -> str:
    """
    Update a task's status.

    Args:
        task_id: The task ID
        status: New status (pending, in_progress, awaiting_approval, completed, failed)
        result: Optional result message

    Returns:
        Confirmation or error
    """
    data = _load_json(TASKS_FILE)
    tasks = data.get("tasks", [])

    for task in tasks:
        if task["id"] == task_id:
            task["status"] = status
            if status == "in_progress":
                task["assigned_at"] = datetime.now().isoformat()
            if status in ("completed", "failed"):
                task["completed_at"] = datetime.now().isoformat()
            if result:
                task["result"] = result

            _save_json(TASKS_FILE, data)
            return f"Task {task_id} updated to {status}"

    return f"Task not found: {task_id}"


# ============== Action Management ==============

def create_pending_action(
    task_id: str,
    action_type: str,
    summary: str,
    details: dict,
    requires_approval: bool = True
) -> str:
    """
    Create a pending action for user approval.

    When requires_approval=True, also creates an approval task in "From Euno"
    project. User can approve by completing the task, or reject by deleting it.

    Args:
        task_id: Associated task ID
        action_type: Type of action (email_send, calendar_create, etc.)
        summary: Human-readable summary of what will happen
        details: Full action details (recipient, content, etc.)
        requires_approval: Whether user must approve before execution

    Returns:
        Confirmation with action ID
    """
    data = _load_json(PENDING_FILE)
    if "actions" not in data:
        data["actions"] = []

    action_id = _generate_id("action")
    action = {
        "id": action_id,
        "task_id": task_id,
        "created": datetime.now().isoformat(),
        "type": action_type,
        "summary": summary,
        "details": details,
        "requires_approval": requires_approval,
        "status": "pending_approval" if requires_approval else "approved",
        "approved_at": None if requires_approval else datetime.now().isoformat(),
        "approved_by": None if requires_approval else "auto",
        "rejected_at": None,
        "rejected_reason": None,
        "executed_at": None,
        "result": None
    }

    data["actions"].append(action)
    _save_json(PENDING_FILE, data)

    # If approval is required, create an approval task in From Euno project
    # User can approve by completing the task, or reject by deleting it
    if requires_approval:
        from ..shared.notifications import create_approval_task

        # Format details for display
        details_str = details if isinstance(details, str) else "\n".join(
            f"- **{k}:** {v}" for k, v in details.items()
        )

        create_approval_task(
            agent_name="worker",
            action_id=action_id,
            action_type=action_type,
            summary=summary,
            details=details_str,
            priority="normal"
        )

    status_msg = "awaiting approval (check From Euno)" if requires_approval else "auto-approved"
    return f"Action created: {action_id}\nType: {action_type}\nSummary: {summary}\nStatus: {status_msg}"


def get_pending_actions(task_id: str = "") -> str:
    """
    Get pending actions awaiting approval or execution.

    Args:
        task_id: Optional filter by task ID

    Returns:
        Formatted list of pending actions
    """
    data = _load_json(PENDING_FILE)
    actions = data.get("actions", [])

    # Filter by task if specified
    if task_id:
        actions = [a for a in actions if a["task_id"] == task_id]

    # Filter to pending/approved (not yet executed)
    actions = [a for a in actions if a["status"] in ("pending_approval", "approved")]

    if not actions:
        return "No pending actions."

    lines = [f"Pending Actions ({len(actions)}):"]
    for action in actions:
        status_icon = "?" if action["status"] == "pending_approval" else "✓"
        lines.append(f"\n[{action['id']}] {status_icon} {action['status'].upper()}")
        lines.append(f"  Type: {action['type']}")
        lines.append(f"  Summary: {action['summary']}")
        lines.append(f"  Task: {action['task_id']}")
        if action["status"] == "pending_approval":
            lines.append("  → Awaiting user approval")
        else:
            lines.append("  → Ready for execution")

    return "\n".join(lines)


def get_action(action_id: str) -> Optional[dict]:
    """
    Get a specific action by ID.

    Args:
        action_id: The action ID

    Returns:
        Action dict or None
    """
    data = _load_json(PENDING_FILE)
    for action in data.get("actions", []):
        if action["id"] == action_id:
            return action

    # Check completed
    data = _load_json(COMPLETED_FILE)
    for action in data.get("actions", []):
        if action["id"] == action_id:
            return action

    return None


def approve_action(action_id: str) -> str:
    """
    Approve a pending action for execution.

    Args:
        action_id: The action ID to approve

    Returns:
        Confirmation or error
    """
    data = _load_json(PENDING_FILE)
    actions = data.get("actions", [])

    for action in actions:
        if action["id"] == action_id:
            if action["status"] != "pending_approval":
                return f"Action {action_id} is not pending approval (status: {action['status']})"

            action["status"] = "approved"
            action["approved_at"] = datetime.now().isoformat()
            action["approved_by"] = "user"

            _save_json(PENDING_FILE, data)
            return f"Action {action_id} approved. Ready for execution.\nSummary: {action['summary']}"

    return f"Action not found: {action_id}"


def reject_action(action_id: str, reason: str = "") -> str:
    """
    Reject a pending action.

    Args:
        action_id: The action ID to reject
        reason: Optional reason for rejection

    Returns:
        Confirmation or error
    """
    data = _load_json(PENDING_FILE)
    actions = data.get("actions", [])

    for action in actions:
        if action["id"] == action_id:
            if action["status"] != "pending_approval":
                return f"Action {action_id} is not pending approval (status: {action['status']})"

            action["status"] = "rejected"
            action["rejected_at"] = datetime.now().isoformat()
            action["rejected_reason"] = reason

            # Move to completed
            _move_to_completed(action)

            # Remove from pending
            data["actions"] = [a for a in actions if a["id"] != action_id]
            _save_json(PENDING_FILE, data)

            return f"Action {action_id} rejected.\nReason: {reason or 'No reason provided'}"

    return f"Action not found: {action_id}"


def mark_action_executed(action_id: str, result: str) -> str:
    """
    Mark an action as executed and move to completed.

    Args:
        action_id: The action ID
        result: Execution result

    Returns:
        Confirmation or error
    """
    data = _load_json(PENDING_FILE)
    actions = data.get("actions", [])

    for action in actions:
        if action["id"] == action_id:
            action["status"] = "executed"
            action["executed_at"] = datetime.now().isoformat()
            action["result"] = result

            # Move to completed
            _move_to_completed(action)

            # Remove from pending
            data["actions"] = [a for a in actions if a["id"] != action_id]
            _save_json(PENDING_FILE, data)

            return f"Action {action_id} executed.\nResult: {result}"

    return f"Action not found: {action_id}"


def _move_to_completed(action: dict):
    """Move an action to the completed file."""
    data = _load_json(COMPLETED_FILE)
    if "actions" not in data:
        data["actions"] = []
    data["actions"].append(action)
    _save_json(COMPLETED_FILE, data)


def get_action_history(task_id: str = "", limit: int = 50) -> str:
    """
    Get completed action history.

    Args:
        task_id: Optional filter by task ID
        limit: Maximum number to return

    Returns:
        Formatted history
    """
    data = _load_json(COMPLETED_FILE)
    actions = data.get("actions", [])

    if task_id:
        actions = [a for a in actions if a["task_id"] == task_id]

    # Sort by execution time (newest first)
    actions.sort(key=lambda a: a.get("executed_at") or a.get("rejected_at") or "", reverse=True)
    actions = actions[:limit]

    if not actions:
        return "No action history."

    lines = [f"Action History ({len(actions)}):"]
    for action in actions:
        status_icon = "✓" if action["status"] == "executed" else "✗"
        lines.append(f"\n[{action['id']}] {status_icon} {action['status'].upper()}")
        lines.append(f"  Type: {action['type']}")
        lines.append(f"  Summary: {action['summary']}")
        if action.get("result"):
            lines.append(f"  Result: {action['result']}")
        if action.get("rejected_reason"):
            lines.append(f"  Rejected: {action['rejected_reason']}")

    return "\n".join(lines)


# ============== Integration Status ==============

def get_integration_status() -> str:
    """
    Get status of external integrations.

    Returns:
        Integration configuration status
    """
    config = _load_json(CONFIG_FILE)

    lines = ["Integration Status:"]
    for name, settings in config.items():
        provider = settings.get("provider", "unknown")
        status = "MOCK" if provider == "mock" else "LIVE"
        lines.append(f"  {name}: {status} ({provider})")

    return "\n".join(lines)


def get_integration_config(integration: str) -> dict:
    """Get config for a specific integration."""
    config = _load_json(CONFIG_FILE)
    return config.get(integration, {"provider": "mock", "config": {}})


# ============== Tool Definitions ==============

WORKER_TOOLS = [
    # Note: create_task, get_tasks, get_task, update_task_status are now in TASK_TOOLS
    # to avoid duplicate tool names when combining lists
    {
        "name": "create_pending_action",
        "description": "Create a pending action for user approval. Actions represent concrete work like sending an email or creating a calendar event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Associated task ID"
                },
                "action_type": {
                    "type": "string",
                    "description": "Type of action (email_send, email_draft, calendar_create, calendar_update, reminder_set, research_query)"
                },
                "summary": {
                    "type": "string",
                    "description": "Human-readable summary of what will happen"
                },
                "details": {
                    "type": "object",
                    "description": "Full action details (varies by type)"
                },
                "requires_approval": {
                    "type": "boolean",
                    "description": "Whether user must approve (default true, false for read-only)"
                }
            },
            "required": ["task_id", "action_type", "summary", "details"]
        }
    },
    {
        "name": "get_pending_actions",
        "description": "Get pending actions awaiting approval or execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Optional filter by task ID"
                }
            }
        }
    },
    {
        "name": "approve_action",
        "description": "Approve a pending action for execution. Only call this when user explicitly approves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action_id": {
                    "type": "string",
                    "description": "The action ID to approve"
                }
            },
            "required": ["action_id"]
        }
    },
    {
        "name": "reject_action",
        "description": "Reject a pending action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action_id": {
                    "type": "string",
                    "description": "The action ID to reject"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for rejection"
                }
            },
            "required": ["action_id"]
        }
    },
    {
        "name": "mark_action_executed",
        "description": "Mark an action as executed after successful completion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action_id": {
                    "type": "string",
                    "description": "The action ID"
                },
                "result": {
                    "type": "string",
                    "description": "Execution result"
                }
            },
            "required": ["action_id", "result"]
        }
    },
    {
        "name": "get_action_history",
        "description": "Get completed action history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Optional filter by task ID"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number to return"
                }
            }
        }
    },
    {
        "name": "get_integration_status",
        "description": "Get status of external integrations (mock vs live).",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

WORKER_HANDLERS = {
    # Action management
    "create_pending_action": create_pending_action,
    "get_pending_actions": get_pending_actions,
    "approve_action": approve_action,
    "reject_action": reject_action,
    "mark_action_executed": mark_action_executed,
    "get_action_history": get_action_history,
    "get_integration_status": get_integration_status,
    # New task system (using autonomous handlers to exclude dangerous bulk delete)
    **AUTONOMOUS_TASK_HANDLERS,
    # Project system
    **PROJECT_HANDLERS,
    # Results
    "store_result": store_result,
    "get_recent_results": get_recent_results,
}

# Extended tools including project and new task system
# Uses AUTONOMOUS_TASK_TOOLS to exclude dangerous bulk-delete operations
EXTENDED_WORKER_TOOLS = WORKER_TOOLS + AUTONOMOUS_TASK_TOOLS + PROJECT_TOOLS + [
    {
        "name": "store_result",
        "description": "Store the result of completed work for a task. Use after autonomous execution or preparing materials.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID this result is for"
                },
                "summary": {
                    "type": "string",
                    "description": "Brief summary of what was accomplished"
                },
                "content": {
                    "type": "object",
                    "description": "Structured content of the result"
                },
                "recommendations": {
                    "type": "string",
                    "description": "Optional next steps"
                }
            },
            "required": ["task_id", "summary", "content"]
        }
    }
    # Note: get_recent_results is already in TASK_TOOLS
]
