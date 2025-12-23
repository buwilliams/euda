"""
Agent Activity Logging System.

Provides logging and querying of agent activities. Each agent writes to
a daily log file tracking their actions, decisions, and outcomes.

Log structure:
data/agents/logs/{agent_name}/{yyyy-mm-dd}.json

Each log entry contains:
- timestamp: ISO format datetime
- action: Type of action (check_work, do_work, tool_call, signal_sent, etc.)
- details: Action-specific information
- outcome: Result or status
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Base paths - Agent logs are shared
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
AGENT_LOGS_DIR = SHARED_DIR / "logs"

# Ensure directory exists
AGENT_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _get_log_path(agent_name: str, date: Optional[str] = None) -> Path:
    """Get the log file path for an agent on a specific date."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    agent_dir = AGENT_LOGS_DIR / agent_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    agent_dir.mkdir(parents=True, exist_ok=True)

    return agent_dir / f"{date}.json"


def _load_log(agent_name: str, date: Optional[str] = None) -> list:
    """Load log entries for an agent on a specific date."""
    log_path = _get_log_path(agent_name, date)

    if log_path.exists():
        with open(log_path, 'r') as f:
            return json.load(f)
    return []


def _save_log(agent_name: str, entries: list, date: Optional[str] = None):
    """Save log entries for an agent."""
    log_path = _get_log_path(agent_name, date)

    with open(log_path, 'w') as f:
        json.dump(entries, f, indent=2)


def log_activity(
    agent_name: str,
    action: str,
    details: Optional[dict] = None,
    outcome: Optional[str] = None
) -> None:
    """
    Log an agent activity.

    Args:
        agent_name: Name of the agent
        action: Type of action (check_work, do_work, tool_call, signal_sent, etc.)
        details: Action-specific information
        outcome: Result or status message
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details or {},
        "outcome": outcome
    }

    entries = _load_log(agent_name)
    entries.append(entry)
    _save_log(agent_name, entries)


def log_tool_call(
    agent_name: str,
    tool_name: str,
    tool_input: dict,
    result: str,
    success: bool = True
) -> None:
    """Log a tool call by an agent."""
    log_activity(
        agent_name=agent_name,
        action="tool_call",
        details={
            "tool": tool_name,
            "input": tool_input,
            "success": success
        },
        outcome=result[:500] if result else None  # Truncate long results
    )


def log_work_check(agent_name: str, work_needed: bool, reason: str = "") -> None:
    """Log a work check by an agent."""
    log_activity(
        agent_name=agent_name,
        action="check_work",
        details={"work_needed": work_needed, "reason": reason},
        outcome="work_required" if work_needed else "idle"
    )


def log_work_start(agent_name: str, task_description: str) -> None:
    """Log when an agent starts work."""
    log_activity(
        agent_name=agent_name,
        action="work_start",
        details={"task": task_description},
        outcome="started"
    )


def log_work_complete(agent_name: str, result: str) -> None:
    """Log when an agent completes work."""
    log_activity(
        agent_name=agent_name,
        action="work_complete",
        details={},
        outcome=result
    )


def log_signal_sent(agent_name: str, signal_name: str) -> None:
    """Log when an agent sends a signal."""
    log_activity(
        agent_name=agent_name,
        action="signal_sent",
        details={"signal": signal_name},
        outcome="sent"
    )


def log_signal_received(agent_name: str, signal_name: str) -> None:
    """Log when an agent receives a signal."""
    log_activity(
        agent_name=agent_name,
        action="signal_received",
        details={"signal": signal_name},
        outcome="received"
    )


def log_error(agent_name: str, error_message: str, context: dict = None) -> None:
    """Log an error encountered by an agent."""
    log_activity(
        agent_name=agent_name,
        action="error",
        details={"context": context or {}},
        outcome=error_message
    )


def log_task_pickup(agent_name: str, task_id: str, task_description: str) -> None:
    """Log when an agent picks up a task."""
    log_activity(
        agent_name=agent_name,
        action="task_pickup",
        details={"task_id": task_id, "description": task_description},
        outcome="picked_up"
    )


def log_task_complete(agent_name: str, task_id: str, result_summary: str) -> None:
    """Log when an agent completes a task."""
    log_activity(
        agent_name=agent_name,
        action="task_complete",
        details={"task_id": task_id},
        outcome=result_summary
    )


# ============== Reading Logs ==============

def get_agent_log(agent_name: str, date: Optional[str] = None) -> str:
    """
    Get formatted log entries for an agent on a specific date.

    Args:
        agent_name: Name of the agent
        date: Date in YYYY-MM-DD format (default: today)

    Returns:
        Formatted log entries
    """
    entries = _load_log(agent_name, date)

    if not entries:
        return f"No activity logged for {agent_name} on {date or 'today'}."

    output = [f"## {agent_name} Activity Log ({date or datetime.now().strftime('%Y-%m-%d')})\n"]
    output.append(f"Total entries: {len(entries)}\n")

    for entry in entries:
        time = entry["timestamp"].split("T")[1].split(".")[0]
        action = entry["action"]
        outcome = entry.get("outcome", "")

        # Format based on action type
        if action == "tool_call":
            tool = entry["details"].get("tool", "unknown")
            output.append(f"- [{time}] Called tool `{tool}`: {outcome[:100]}")
        elif action == "task_pickup":
            desc = entry["details"].get("description", "")[:50]
            output.append(f"- [{time}] Picked up task: {desc}")
        elif action == "task_complete":
            output.append(f"- [{time}] Completed task: {outcome[:100]}")
        elif action == "work_start":
            task = entry["details"].get("task", "")[:50]
            output.append(f"- [{time}] Started work: {task}")
        elif action == "work_complete":
            output.append(f"- [{time}] Completed work: {outcome[:100]}")
        elif action == "signal_sent":
            signal = entry["details"].get("signal", "")
            output.append(f"- [{time}] Sent signal: {signal}")
        elif action == "check_work":
            needed = entry["details"].get("work_needed", False)
            output.append(f"- [{time}] Checked for work: {'work needed' if needed else 'idle'}")
        elif action == "error":
            output.append(f"- [{time}] ERROR: {outcome[:100]}")
        else:
            output.append(f"- [{time}] {action}: {outcome[:100]}")

    return "\n".join(output)


def get_all_agent_logs(date: Optional[str] = None) -> str:
    """
    Get logs from all agents for a specific date.

    Args:
        date: Date in YYYY-MM-DD format (default: today)

    Returns:
        Combined formatted logs from all agents
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    output = [f"# All Agent Activity ({date})\n"]

    # Find all agent log directories
    if not AGENT_LOGS_DIR.exists():
        return "No agent logs found."

    agents_with_logs = []
    for agent_dir in AGENT_LOGS_DIR.iterdir():
        if agent_dir.is_dir():
            log_file = agent_dir / f"{date}.json"
            if log_file.exists():
                agents_with_logs.append(agent_dir.name)

    if not agents_with_logs:
        return f"No agent activity logged for {date}."

    for agent_name in sorted(agents_with_logs):
        output.append(get_agent_log(agent_name, date))
        output.append("")

    return "\n".join(output)


def get_recent_agent_activity(agent_name: str, limit: int = 20) -> str:
    """
    Get the most recent activity entries for an agent.

    Args:
        agent_name: Name of the agent
        limit: Maximum number of entries to return

    Returns:
        Formatted recent activity
    """
    # Start with today and go back up to 7 days
    entries = []
    date = datetime.now()

    for _ in range(7):
        date_str = date.strftime("%Y-%m-%d")
        day_entries = _load_log(agent_name, date_str)
        for entry in day_entries:
            entry["_date"] = date_str
        entries.extend(day_entries)
        date -= timedelta(days=1)

        if len(entries) >= limit:
            break

    # Sort by timestamp descending and limit
    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    entries = entries[:limit]

    if not entries:
        return f"No recent activity for {agent_name}."

    output = [f"## Recent {agent_name} Activity (last {len(entries)} entries)\n"]

    for entry in entries:
        date = entry["_date"]
        time = entry["timestamp"].split("T")[1].split(".")[0]
        action = entry["action"]
        outcome = entry.get("outcome", "")

        output.append(f"- [{date} {time}] {action}: {outcome[:80]}")

    return "\n".join(output)


def search_agent_logs(
    query: str,
    agent_name: Optional[str] = None,
    days_back: int = 7
) -> str:
    """
    Search agent logs for specific content.

    Args:
        query: Text to search for (case-insensitive)
        agent_name: Optional - search only this agent's logs
        days_back: How many days to search

    Returns:
        Matching log entries
    """
    query_lower = query.lower()
    matches = []
    date = datetime.now()

    # Determine which agents to search
    if agent_name:
        agent_dirs = [AGENT_LOGS_DIR / agent_name.lower().replace(" ", "_")]
    else:
        agent_dirs = [d for d in AGENT_LOGS_DIR.iterdir() if d.is_dir()]

    for _ in range(days_back):
        date_str = date.strftime("%Y-%m-%d")

        for agent_dir in agent_dirs:
            if not agent_dir.exists():
                continue

            log_file = agent_dir / f"{date_str}.json"
            if not log_file.exists():
                continue

            with open(log_file, 'r') as f:
                entries = json.load(f)

            for entry in entries:
                # Search in action, outcome, and details
                entry_text = json.dumps(entry).lower()
                if query_lower in entry_text:
                    matches.append({
                        "agent": agent_dir.name,
                        "date": date_str,
                        "entry": entry
                    })

        date -= timedelta(days=1)

    if not matches:
        return f"No matches found for '{query}' in the last {days_back} days."

    output = [f"## Search Results for '{query}' ({len(matches)} matches)\n"]

    for match in matches[:50]:  # Limit results
        agent = match["agent"]
        date = match["date"]
        entry = match["entry"]
        time = entry["timestamp"].split("T")[1].split(".")[0]
        action = entry["action"]
        outcome = entry.get("outcome", "")

        output.append(f"- [{agent}] [{date} {time}] {action}: {outcome[:60]}")

    if len(matches) > 50:
        output.append(f"\n... and {len(matches) - 50} more matches")

    return "\n".join(output)


def get_agent_task_status(task_id: str) -> str:
    """
    Check if any agent has picked up or completed a specific task.

    Args:
        task_id: The task ID to search for

    Returns:
        Status information about the task
    """
    return search_agent_logs(task_id, days_back=14)


def get_agent_summary(agent_name: str, days: int = 1) -> str:
    """
    Get a summary of agent activity over the specified period.

    Args:
        agent_name: Name of the agent
        days: Number of days to summarize

    Returns:
        Summary of agent activity
    """
    action_counts = {}
    total_entries = 0
    errors = 0
    tasks_completed = 0
    signals_sent = []

    date = datetime.now()
    for _ in range(days):
        date_str = date.strftime("%Y-%m-%d")
        entries = _load_log(agent_name, date_str)

        for entry in entries:
            total_entries += 1
            action = entry["action"]
            action_counts[action] = action_counts.get(action, 0) + 1

            if action == "error":
                errors += 1
            elif action == "task_complete":
                tasks_completed += 1
            elif action == "signal_sent":
                signals_sent.append(entry["details"].get("signal", "unknown"))

        date -= timedelta(days=1)

    if total_entries == 0:
        return f"No activity for {agent_name} in the last {days} day(s)."

    output = [f"## {agent_name} Summary (last {days} day(s))\n"]
    output.append(f"Total activities: {total_entries}")
    output.append(f"Tasks completed: {tasks_completed}")
    output.append(f"Errors: {errors}")

    if signals_sent:
        output.append(f"Signals sent: {', '.join(set(signals_sent))}")

    output.append("\nActivity breakdown:")
    for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
        output.append(f"  - {action}: {count}")

    return "\n".join(output)


# ============== Tool Definitions ==============

AGENT_LOG_TOOLS = [
    {
        "name": "get_agent_log",
        "description": "Get the activity log for a specific agent on a specific date. Shows what the agent has been doing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent (e.g., 'worker', 'attention', 'ingestion')"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (default: today)"
                }
            },
            "required": ["agent_name"]
        }
    },
    {
        "name": "get_all_agent_logs",
        "description": "Get activity logs from all agents for a specific date. Good for understanding overall system activity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (default: today)"
                }
            }
        }
    },
    {
        "name": "get_recent_agent_activity",
        "description": "Get the most recent activity entries for an agent across multiple days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum entries to return (default: 20)"
                }
            },
            "required": ["agent_name"]
        }
    },
    {
        "name": "search_agent_logs",
        "description": "Search agent logs for specific content like task IDs, tool names, or keywords.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search for"
                },
                "agent_name": {
                    "type": "string",
                    "description": "Optional - search only this agent's logs"
                },
                "days_back": {
                    "type": "integer",
                    "description": "How many days to search (default: 7)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_agent_task_status",
        "description": "Check if any agent has picked up or worked on a specific task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to check"
                }
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "get_agent_summary",
        "description": "Get a summary of an agent's activity over a period of time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to summarize (default: 1)"
                }
            },
            "required": ["agent_name"]
        }
    }
]

AGENT_LOG_HANDLERS = {
    "get_agent_log": get_agent_log,
    "get_all_agent_logs": get_all_agent_logs,
    "get_recent_agent_activity": get_recent_agent_activity,
    "search_agent_logs": search_agent_logs,
    "get_agent_task_status": get_agent_task_status,
    "get_agent_summary": get_agent_summary,
}
