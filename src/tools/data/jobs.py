"""
Job Tools - CRUD operations for jobs.

Jobs are the primary unit of work in the system.
They can be nested via parent_id to form hierarchies.

Storage: SQLite database at data/jobs/db.sqlite
"""

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from .. import tool


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
JOBS_DIR = DATA_DIR / "jobs"
DB_PATH = JOBS_DIR / "db.sqlite"

# Thread-local storage for database connections
_local = threading.local()


def _clear_connection():
    """Clear thread-local connection. Call after fresh-start/restore."""
    if hasattr(_local, 'connection') and _local.connection is not None:
        try:
            _local.connection.close()
        except Exception:
            pass
        _local.connection = None


def _get_connection() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    if not hasattr(_local, 'connection') or _local.connection is None:
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.connection = conn
    return _local.connection


@contextmanager
def _transaction():
    """Context manager for database transactions."""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _ensure_schema():
    """Create tables if they don't exist."""
    conn = _get_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'working', 'done', 'error', 'archived')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT 'user',
            description TEXT,
            due_date TEXT,
            someday INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            tags TEXT
        );

        CREATE TABLE IF NOT EXISTS job_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            timestamp TEXT NOT NULL,
            agent TEXT NOT NULL,
            action TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_parent_id ON jobs(parent_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id);
    ''')
    conn.commit()

    # Migration: add assignees column if it doesn't exist
    try:
        conn.execute("SELECT assignees FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE jobs ADD COLUMN assignees TEXT")
        conn.commit()

    # Migration: add in_progress_by column if it doesn't exist
    try:
        conn.execute("SELECT in_progress_by FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE jobs ADD COLUMN in_progress_by TEXT")
        conn.commit()

    # Migration: add agent_id column if it doesn't exist (for agent inbox jobs)
    try:
        conn.execute("SELECT agent_id FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE jobs ADD COLUMN agent_id TEXT")
        conn.commit()

    # Migration: add pending_from column if it doesn't exist (for job handoff tracking)
    try:
        conn.execute("SELECT pending_from FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE jobs ADD COLUMN pending_from TEXT")
        conn.commit()

    # Migration: rename 'completed' status to 'done' and update CHECK constraint
    # SQLite doesn't support ALTER TABLE to change constraints, so we check and migrate data
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'completed'")
        completed_count = cursor.fetchone()[0]
        if completed_count > 0:
            conn.execute("UPDATE jobs SET status = 'done' WHERE status = 'completed'")
            conn.commit()
            print(f"Migrated {completed_count} jobs from 'completed' to 'done' status")
    except Exception:
        pass  # Table may not exist yet


# Initialize schema on module import
_ensure_schema()


def _emit_event(event: str, scope: str = None, data: dict = None):
    """Emit an event to the event bus."""
    from ...web.events import emit_event
    emit_event(event, scope=scope, data=data)


def _emit_jobs_update():
    """Notify UI clients that jobs have changed."""
    from ...web.events import emit_ui_event
    all_jobs = list_jobs()
    emit_ui_event("jobs_update", {"jobs": all_jobs})


def _notify_agent_has_jobs(agent_id: str):
    """Notify the job cache that an agent has pending jobs."""
    from ...agent.manager import get_manager
    manager = get_manager()
    if manager:
        manager.agents_with_jobs[agent_id] = True


def _row_to_job(row: sqlite3.Row, logs: List[dict] = None) -> dict:
    """Convert a database row to a job dictionary."""
    # Handle columns that may not exist in older schemas
    assignees_raw = row["assignees"] if "assignees" in row.keys() else None
    in_progress_by = row["in_progress_by"] if "in_progress_by" in row.keys() else None
    agent_id = row["agent_id"] if "agent_id" in row.keys() else None
    pending_from = row["pending_from"] if "pending_from" in row.keys() else None

    job = {
        "id": row["id"],
        "name": row["name"],
        "parent_id": row["parent_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "created_by": row["created_by"],
        "description": row["description"],
        "due_date": row["due_date"],
        "someday": bool(row["someday"]),
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "assignees": json.loads(assignees_raw) if assignees_raw else [],
        "in_progress_by": in_progress_by,
        "agent_id": agent_id,
        "pending_from": pending_from,
        "log": logs if logs is not None else []
    }
    if row["completed_at"]:
        job["completed_at"] = row["completed_at"]
    return job


def _get_job_logs(job_id: str) -> List[dict]:
    """Get all log entries for a job."""
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT timestamp, agent, action FROM job_logs WHERE job_id = ? ORDER BY id",
        (job_id,)
    )
    return [{"timestamp": row[0], "agent": row[1], "action": row[2]} for row in cursor]


def _load_job(job_id: str) -> Optional[dict]:
    """Load a job by ID."""
    conn = _get_connection()
    cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    if row:
        logs = _get_job_logs(job_id)
        return _row_to_job(row, logs)
    return None


@tool("list_jobs", "List all jobs, optionally filtered by status, parent, tag, assignee, or actionable due date. Use when: reviewing work queue, finding assigned jobs, checking project status.", tool_type="data")
def list_jobs(status: str = None, parent_id: str = None, tag: str = None, assignee: str = None, actionable: bool = False) -> List[dict]:
    """List jobs with optional filters.

    Args:
        status: Filter by status (todo, working, done, error, archived)
        parent_id: Filter by parent job ID (empty string for root jobs)
        tag: Filter to jobs containing this tag
        assignee: Filter to jobs assigned to this agent ID
        actionable: If True, only return jobs with due_date <= today or NULL, and not someday
    """
    from datetime import date

    conn = _get_connection()

    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if parent_id is not None:
        if parent_id == "":
            query += " AND parent_id IS NULL"
        else:
            query += " AND parent_id = ?"
            params.append(parent_id)

    if tag:
        # Filter jobs that have the specified tag in their tags JSON array
        query += " AND EXISTS (SELECT 1 FROM json_each(tags) WHERE json_each.value = ?)"
        params.append(tag)

    if assignee:
        # Filter jobs that have the specified agent in their assignees JSON array
        query += " AND EXISTS (SELECT 1 FROM json_each(assignees) WHERE json_each.value = ?)"
        params.append(assignee)
        # Exclude system jobs - only their descendants should be processed by agents
        query += " AND NOT EXISTS (SELECT 1 FROM json_each(tags) WHERE json_each.value IN ('system:agents', 'system:projects', 'system:system', 'agent-inbox'))"

    if actionable:
        # Only jobs that are due today, past, or have no due date (and not someday)
        today = date.today().isoformat()
        query += " AND (due_date IS NULL OR due_date <= ?)"
        params.append(today)
        query += " AND someday = 0"
        # Exclude jobs with blocking tags (waiting:* or blocked:*)
        query += " AND NOT EXISTS (SELECT 1 FROM json_each(tags) WHERE json_each.value LIKE 'waiting:%' OR json_each.value LIKE 'blocked:%')"
        # Exclude jobs already claimed by another agent
        if assignee:
            query += " AND (in_progress_by IS NULL OR in_progress_by = ?)"
            params.append(assignee)
        else:
            query += " AND in_progress_by IS NULL"

    query += " ORDER BY updated_at DESC"

    cursor = conn.execute(query, params)
    jobs = []
    for row in cursor:
        logs = _get_job_logs(row["id"])
        jobs.append(_row_to_job(row, logs))

    return jobs


@tool("get_job", "Get a job by its ID with full details. Use when: need complete job info including logs and attachments.", tool_type="data")
def get_job(job_id: str) -> Optional[dict]:
    """Get a single job by ID."""
    return _load_job(job_id)


def get_agent_inbox_job(agent_id: str) -> Optional[dict]:
    """Get an agent's inbox job (under the Agents container)."""
    all_jobs = list_jobs()
    for job in all_jobs:
        if job.get("agent_id") == agent_id:
            return job
    return None


def _get_default_parent_for_creator(created_by: str) -> Optional[str]:
    """Get the default parent job ID based on who is creating the job.

    - user/chat -> Projects container
    - other agents -> their agent inbox job
    """
    from ..agents.agents import list_agents

    # User or Chat agent -> Projects
    if created_by in ("user", "chat", "system"):
        projects = get_projects_container()
        return projects["id"] if projects else None

    # Check if created_by is a known agent
    agents = list_agents()
    agent_ids = {a["id"] for a in agents}

    if created_by in agent_ids:
        # Agent -> their inbox job
        inbox = get_agent_inbox_job(created_by)
        return inbox["id"] if inbox else None

    # Unknown creator -> Projects as fallback
    projects = get_projects_container()
    return projects["id"] if projects else None


@tool("create_job", "Create a new job with optional parent, tags, assignees, and due date. Use when: breaking down work, creating tasks for yourself or other agents.", tool_type="data")
def create_job(
    name: str,
    description: str = None,
    parent_id: str = None,
    tags: list = None,
    assignees: list = None,
    due_date: str = None,
    someday: bool = False,
    created_by: str = "user"
) -> dict:
    """Create a new job.

    If no parent_id is provided:
    - Jobs created by user/chat go under Projects
    - Jobs created by other agents go under their agent inbox
    """
    now = datetime.utcnow().isoformat() + "Z"
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    # Set default parent if none provided
    effective_parent_id = parent_id
    if effective_parent_id is None:
        effective_parent_id = _get_default_parent_for_creator(created_by)

    with _transaction() as conn:
        conn.execute('''
            INSERT INTO jobs (id, name, parent_id, status, created_at, updated_at,
                            created_by, description, due_date, someday, tags, assignees)
            VALUES (?, ?, ?, 'todo', ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_id, name, effective_parent_id, now, now, created_by,
            description, due_date, int(someday), json.dumps(tags or []),
            json.dumps(assignees or [])
        ))

        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'created')
        ''', (job_id, now, created_by))

    # Emit job:created (broadcast) and job:assigned (scoped) events
    job = _load_job(job_id)
    _emit_event("job:created", data={"job_id": job_id, "name": name})
    for agent_id in (assignees or []):
        _emit_event("job:assigned", scope=agent_id, data={"job_id": job_id, "name": name})
        _notify_agent_has_jobs(agent_id)

    # Notify UI clients
    _emit_jobs_update()

    return job


@tool("update_job", "Update a job's fields (name, description, status, tags, assignees, due date). Use when: modifying job details, changing assignments, rescheduling.", tool_type="data")
def update_job(
    job_id: str,
    name: str = None,
    description: str = None,
    status: str = None,
    tags: list = None,
    assignees: list = None,
    due_date: str = None,
    someday: bool = None
) -> Optional[dict]:
    """Update a job's fields."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    # Prevent status changes on system jobs
    system_tags = {"system:agents", "system:projects", "system:system", "agent-inbox"}
    if status is not None and any(tag in system_tags for tag in job.get("tags", [])):
        return {"error": "Cannot change status of system jobs"}

    now = datetime.utcnow().isoformat() + "Z"

    updates = ["updated_at = ?"]
    params = [now]

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(tags))
    if assignees is not None:
        updates.append("assignees = ?")
        params.append(json.dumps(assignees))
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date if due_date else None)  # Empty string means clear
    if someday is not None:
        updates.append("someday = ?")
        params.append(int(someday))

    params.append(job_id)

    with _transaction() as conn:
        conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params)

    # Emit job:assigned events for newly assigned agents
    if assignees is not None:
        old_assignees = set(job.get("assignees", []))
        new_assignees = set(assignees) - old_assignees
        for agent_id in new_assignees:
            _emit_event("job:assigned", scope=agent_id, data={"job_id": job_id, "name": job["name"]})
            _notify_agent_has_jobs(agent_id)

    # Notify UI clients
    _emit_jobs_update()

    return _load_job(job_id)


@tool("handoff_job", "Pass a job to another agent or user for review/action. Tracks who it came from so they can receive it back.", tool_type="data")
def handoff_job(job_id: str, to: str, note: str = None, agent: str = "user") -> Optional[dict]:
    """Hand off a job to another agent or user.

    This is the primary mechanism for job coordination between agents.
    It sets the assignee to the target and records who sent it so the
    job can be returned to them.

    Args:
        job_id: The job to hand off
        to: Agent ID or "user" to hand off to
        note: Optional note explaining what's needed or what was done
        agent: Who is performing the handoff (for logging)

    Returns:
        Updated job dict or error
    """
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    now = datetime.utcnow().isoformat() + "Z"

    # Update assignees and pending_from
    with _transaction() as conn:
        conn.execute('''
            UPDATE jobs SET assignees = ?, pending_from = ?, updated_at = ?
            WHERE id = ?
        ''', (json.dumps([to]), agent, now, job_id))

        # Add log entry
        action = f"Handed off to {to}"
        if note:
            action += f": {note}"
        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, ?)
        ''', (job_id, now, agent, action))

    # Emit job:assigned event for the target
    _emit_event("job:assigned", scope=to, data={"job_id": job_id, "name": job["name"]})
    if to != "user":
        _notify_agent_has_jobs(to)

    # Notify UI clients
    _emit_jobs_update()

    return _load_job(job_id)


@tool("complete_job", "Mark a job as done. Use when: work is finished and verified, task is no longer needed.", tool_type="data")
def complete_job(job_id: str, agent: str = "user") -> Optional[dict]:
    """Mark a job as done."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    # Prevent completing system jobs (containers and agent inboxes)
    # Exception: Allow completing trigger jobs even if they have system tags
    is_trigger = job.get("name", "").startswith("Trigger:")
    if not is_trigger:
        system_tags = {"system:agents", "system:projects", "system:system", "agent-inbox"}
        if any(tag in system_tags for tag in job.get("tags", [])):
            return {"error": "Cannot complete system jobs"}

    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        conn.execute('''
            UPDATE jobs SET status = 'done', completed_at = ?, updated_at = ?
            WHERE id = ?
        ''', (now, now, job_id))

        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'completed')
        ''', (job_id, now, agent))

    # Emit job:completed to each assignee
    for assignee in job.get("assignees", []):
        _emit_event("job:completed", scope=assignee, data={"job_id": job_id, "name": job["name"]})

    # Notify UI clients
    _emit_jobs_update()

    return _load_job(job_id)


@tool("restore_job", "Restore a done job back to todo status. Use when: a done job needs to be reopened.", tool_type="data")
def restore_job(job_id: str, agent: str = "user") -> Optional[dict]:
    """Restore a done job back to todo status."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        conn.execute('''
            UPDATE jobs SET status = 'todo', completed_at = NULL, updated_at = ?
            WHERE id = ?
        ''', (now, job_id))

        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'restored')
        ''', (job_id, now, agent))

    # Notify UI clients
    _emit_jobs_update()

    return _load_job(job_id)


def unblock_job(job_id: str) -> bool:
    """Remove waiting:* and blocked:* tags from a job.

    Called automatically when a user interacts with a blocked job
    (views it, adds an asset, etc.) to put it back in the agent's queue.

    Args:
        job_id: The job to unblock

    Returns:
        True if the job was unblocked, False if it wasn't blocked
    """
    job = _load_job(job_id)
    if not job:
        return False

    tags = job.get("tags", [])
    blocking_tags = [t for t in tags if t.startswith(("waiting:", "blocked:"))]

    if not blocking_tags:
        return False  # Not blocked

    # Remove blocking tags
    new_tags = [t for t in tags if not t.startswith(("waiting:", "blocked:"))]

    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        conn.execute('''
            UPDATE jobs SET tags = ?, updated_at = ?
            WHERE id = ?
        ''', (json.dumps(new_tags), now, job_id))

        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, ?)
        ''', (job_id, now, "user", f"unblocked: {', '.join(blocking_tags)}"))

    # Notify assignees that job is actionable again
    for assignee in job.get("assignees", []):
        _emit_event("job:assigned", scope=assignee, data={"job_id": job_id, "name": job["name"]})
        _notify_agent_has_jobs(assignee)

    # Notify UI clients
    _emit_jobs_update()

    return True


@tool("archive_job", "Archive a job (mark as no longer relevant). Use when: job is obsolete or cancelled.", tool_type="data")
def archive_job(job_id: str, agent: str = "user") -> Optional[dict]:
    """Archive a job."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    # Prevent archiving system jobs (containers and agent inboxes)
    system_tags = {"system:agents", "system:projects", "system:system", "agent-inbox"}
    if any(tag in system_tags for tag in job.get("tags", [])):
        return {"error": "Cannot archive system jobs"}

    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        conn.execute('''
            UPDATE jobs SET status = 'archived', updated_at = ?
            WHERE id = ?
        ''', (now, job_id))

        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'archived')
        ''', (job_id, now, agent))

    # Emit job:archived to each assignee
    for assignee in job.get("assignees", []):
        _emit_event("job:archived", scope=assignee, data={"job_id": job_id, "name": job["name"]})

    # Notify UI clients
    _emit_jobs_update()

    return _load_job(job_id)


@tool("add_job_log", "Add a log entry to a job. Use when: recording progress, notes, or status updates on a job.", tool_type="data")
def add_job_log(job_id: str, action: str, agent: str = "user") -> Optional[dict]:
    """Add a log entry to a job."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (now, job_id))
        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, ?)
        ''', (job_id, now, agent, action))

    # Notify UI clients
    _emit_jobs_update()

    return _load_job(job_id)


def get_job_logs(job_id: str) -> List[dict]:
    """Get all log entries for a job.

    Returns:
        List of log entries with timestamp, agent, and action fields.
        Sorted by timestamp ascending (oldest first).
    """
    conn = _get_connection()
    cursor = conn.execute('''
        SELECT timestamp, agent, action
        FROM job_logs
        WHERE job_id = ?
        ORDER BY timestamp ASC
    ''', (job_id,))

    return [dict(row) for row in cursor.fetchall()]


@tool("get_child_jobs", "Get all child jobs of a parent job. Use when: viewing job hierarchy, checking sub-tasks.", tool_type="data")
def get_child_jobs(parent_id: str) -> List[dict]:
    """Get all child jobs of a given parent."""
    return list_jobs(parent_id=parent_id)


@tool("delete_job", "Delete a job permanently. Use when: removing unwanted jobs (use archive_job for normal cleanup).", tool_type="data")
def delete_job(job_id: str, delete_children: bool = False) -> dict:
    """Delete a job. Optionally delete child jobs too."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    # Prevent deletion of system jobs (containers and agent inboxes)
    system_tags = {"system:agents", "system:projects", "system:system", "agent-inbox"}
    if any(tag in system_tags for tag in job.get("tags", [])):
        return {"error": "Cannot delete system jobs"}

    # Delete children if requested (must do before parent due to FK)
    if delete_children:
        children = get_child_jobs(job_id)
        for child in children:
            delete_job(child["id"], delete_children=True)

    with _transaction() as conn:
        # Delete the job (logs cascade automatically via ON DELETE CASCADE)
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    # Notify UI clients
    _emit_jobs_update()

    return {"deleted": job_id, "children_deleted": delete_children}


# =============================================================================
# BATCH OPERATIONS - More efficient than multiple single-item calls
# =============================================================================

@tool(
    "create_jobs_batch",
    "Create multiple jobs in a single operation. Use when: creating many related tasks at once for efficiency.",
    input_schema={
        "type": "object",
        "properties": {
            "jobs": {
                "type": "array",
                "description": "List of jobs to create",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Job name (required)"},
                        "description": {"type": "string", "description": "Job description"},
                        "parent_id": {"type": "string", "description": "Parent job ID for sub-jobs"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for the job"},
                        "due_date": {"type": "string", "description": "Due date (ISO format)"},
                        "someday": {"type": "boolean", "description": "Mark as someday/maybe"}
                    },
                    "required": ["name"]
                }
            },
            "created_by": {"type": "string", "description": "Who is creating these jobs"}
        },
        "required": ["jobs"]
    },
    tool_type="data"
)
def create_jobs_batch(jobs: list, created_by: str = "agent") -> dict:
    """Create multiple jobs in a single operation.

    Returns:
        Dict with 'created' (list of job objects), 'count', and 'errors' if any
    """
    results = []
    errors = []

    for i, job_spec in enumerate(jobs):
        try:
            result = create_job(
                name=job_spec["name"],
                description=job_spec.get("description"),
                parent_id=job_spec.get("parent_id"),
                tags=job_spec.get("tags"),
                due_date=job_spec.get("due_date"),
                someday=job_spec.get("someday", False),
                created_by=created_by
            )
            results.append(result)
        except Exception as e:
            errors.append({"index": i, "name": job_spec.get("name"), "error": str(e)})

    return {
        "created": results,
        "count": len(results),
        "errors": errors if errors else None
    }


@tool(
    "update_jobs_batch",
    "Update multiple jobs in a single operation. Use when: bulk updating job fields for efficiency.",
    input_schema={
        "type": "object",
        "properties": {
            "updates": {
                "type": "array",
                "description": "List of job updates",
                "items": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string", "description": "Job ID to update (required)"},
                        "name": {"type": "string", "description": "New job name"},
                        "description": {"type": "string", "description": "New description"},
                        "status": {"type": "string", "enum": ["todo", "working", "done", "error", "archived"], "description": "New status"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "New tags"},
                        "due_date": {"type": "string", "description": "New due date"},
                        "someday": {"type": "boolean", "description": "Someday/maybe flag"}
                    },
                    "required": ["job_id"]
                }
            }
        },
        "required": ["updates"]
    },
    tool_type="data"
)
def update_jobs_batch(updates: list) -> dict:
    """Update multiple jobs in a single operation.

    Returns:
        Dict with 'updated' (list of job objects), 'count', and 'errors' if any
    """
    results = []
    errors = []

    for i, update_spec in enumerate(updates):
        job_id = update_spec.get("job_id")
        if not job_id:
            errors.append({"index": i, "error": "job_id is required"})
            continue

        try:
            # Extract job_id and pass rest as kwargs
            kwargs = {k: v for k, v in update_spec.items() if k != "job_id"}
            result = update_job(job_id, **kwargs)
            if result and "error" not in result:
                results.append(result)
            else:
                errors.append({"index": i, "job_id": job_id, "error": result.get("error", "Unknown error")})
        except Exception as e:
            errors.append({"index": i, "job_id": job_id, "error": str(e)})

    return {
        "updated": results,
        "count": len(results),
        "errors": errors if errors else None
    }


@tool(
    "complete_jobs_batch",
    "Complete multiple jobs in a single operation. Use when: finishing multiple related tasks at once.",
    input_schema={
        "type": "object",
        "properties": {
            "job_ids": {
                "type": "array",
                "description": "List of job IDs to complete",
                "items": {"type": "string"}
            },
            "agent": {"type": "string", "description": "Agent completing the jobs"}
        },
        "required": ["job_ids"]
    },
    tool_type="data"
)
def complete_jobs_batch(job_ids: list, agent: str = "user") -> dict:
    """Complete multiple jobs in a single operation.

    Returns:
        Dict with 'completed' (list of job objects), 'count', and 'errors' if any
    """
    results = []
    errors = []

    for job_id in job_ids:
        try:
            result = complete_job(job_id, agent=agent)
            if result and "error" not in result:
                results.append(result)
            else:
                errors.append({"job_id": job_id, "error": result.get("error", "Unknown error")})
        except Exception as e:
            errors.append({"job_id": job_id, "error": str(e)})

    return {
        "completed": results,
        "count": len(results),
        "errors": errors if errors else None
    }


@tool(
    "add_job_logs_batch",
    "Add log entries to multiple jobs in a single operation. Use when: recording progress on multiple jobs at once.",
    input_schema={
        "type": "object",
        "properties": {
            "logs": {
                "type": "array",
                "description": "List of log entries to add",
                "items": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string", "description": "Job ID (required)"},
                        "action": {"type": "string", "description": "Log action/message (required)"}
                    },
                    "required": ["job_id", "action"]
                }
            },
            "agent": {"type": "string", "description": "Agent adding the logs"}
        },
        "required": ["logs"]
    },
    tool_type="data"
)
def add_job_logs_batch(logs: list, agent: str = "user") -> dict:
    """Add log entries to multiple jobs in a single operation.

    Returns:
        Dict with 'logged' (list of results), 'count', and 'errors' if any
    """
    results = []
    errors = []

    for log_entry in logs:
        job_id = log_entry.get("job_id")
        action = log_entry.get("action")

        if not job_id or not action:
            errors.append({"job_id": job_id, "error": "job_id and action are required"})
            continue

        try:
            result = add_job_log(job_id, action, agent=agent)
            if result and "error" not in result:
                results.append({"job_id": job_id, "logged": True})
            else:
                errors.append({"job_id": job_id, "error": result.get("error", "Unknown error")})
        except Exception as e:
            errors.append({"job_id": job_id, "error": str(e)})

    return {
        "logged": results,
        "count": len(results),
        "errors": errors if errors else None
    }


# =============================================================================
# AGENT ASSIGNMENT AND SYSTEM CONTAINERS
# =============================================================================

@tool("assign_agent", "Assign an agent to a job. Use when: delegating work to another agent.", tool_type="data")
def assign_agent(job_id: str, agent_id: str) -> Optional[dict]:
    """Assign an agent to work on a job. Wakes the agent immediately.

    Args:
        job_id: The job to assign
        agent_id: The agent ID to assign
    """
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    assignees = job.get("assignees", [])
    if agent_id in assignees:
        return {"error": f"Agent {agent_id} already assigned"}

    assignees.append(agent_id)
    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        conn.execute(
            "UPDATE jobs SET assignees = ?, updated_at = ? WHERE id = ?",
            (json.dumps(assignees), now, job_id)
        )
        conn.execute(
            "INSERT INTO job_logs (job_id, timestamp, agent, action) VALUES (?, ?, ?, ?)",
            (job_id, now, "system", f"assigned:{agent_id}")
        )

    # Emit job:assigned event to the agent and notify cache
    _emit_event("job:assigned", scope=agent_id, data={"job_id": job_id, "name": job["name"]})
    _notify_agent_has_jobs(agent_id)

    # Notify UI clients
    _emit_jobs_update()

    return _load_job(job_id)


@tool("unassign_agent", "Remove an agent assignment from a job. Use when: reassigning work or removing delegation.", tool_type="data")
def unassign_agent(job_id: str, agent_id: str) -> Optional[dict]:
    """Remove an agent from a job.

    Args:
        job_id: The job to unassign from
        agent_id: The agent ID to remove
    """
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    assignees = job.get("assignees", [])
    if agent_id not in assignees:
        return {"error": f"Agent {agent_id} not assigned to this job"}

    assignees.remove(agent_id)
    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        conn.execute(
            "UPDATE jobs SET assignees = ?, updated_at = ? WHERE id = ?",
            (json.dumps(assignees), now, job_id)
        )
        conn.execute(
            "INSERT INTO job_logs (job_id, timestamp, agent, action) VALUES (?, ?, ?, ?)",
            (job_id, now, "system", f"unassigned:{agent_id}")
        )

    # Emit job:unassigned event to the agent
    _emit_event("job:unassigned", scope=agent_id, data={"job_id": job_id, "name": job["name"]})

    # Notify UI clients
    _emit_jobs_update()

    return _load_job(job_id)


@tool("list_assignees", "List agents assigned to a job. Use when: checking who is working on a job.", tool_type="data")
def list_assignees(job_id: str) -> list:
    """Get list of agent IDs assigned to a job.

    Args:
        job_id: The job to check
    """
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    return job.get("assignees", [])


@tool("list_available_agents", "List all agent IDs that can be assigned to jobs. Use when: finding agents to assign work to.", tool_type="data")
def list_available_agents() -> list:
    """Get list of all available agent IDs."""
    from ..agents.agents import list_agents
    agents = list_agents()
    return [a["id"] for a in agents]


@tool("claim_job", "Claim a job for exclusive work. Use when: starting work to prevent conflicts.", tool_type="data")
def claim_job(job_id: str, agent_id: str) -> dict:
    """Atomically claim a job to work on it exclusively.

    Uses atomic SQL to prevent TOCTOU race conditions where multiple threads
    could all read "unclaimed" and then all write their claim.

    Returns error if already claimed by another agent.

    Args:
        job_id: The job to claim
        agent_id: The agent claiming the job
    """
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    # Prevent claiming system jobs (containers and agent inboxes)
    # Only their descendants should be processed
    system_tags = {"system:agents", "system:projects", "system:system", "agent-inbox"}
    if any(tag in system_tags for tag in job.get("tags", [])):
        return {"error": "Cannot claim system jobs - only their descendants can be processed"}

    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        # ATOMIC: Update only if unclaimed OR already claimed by us
        # This prevents TOCTOU race where multiple threads read NULL and all claim
        # Also set status to 'working' per spec (docs/3_system.md)
        result = conn.execute(
            """UPDATE jobs SET in_progress_by = ?, status = 'working', updated_at = ?
               WHERE id = ? AND status = 'todo' AND (in_progress_by IS NULL OR in_progress_by = ?)""",
            (agent_id, now, job_id, agent_id)
        )

        if result.rowcount == 0:
            # Failed to claim - either job doesn't exist or someone else has it
            current = conn.execute(
                "SELECT in_progress_by FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if current:
                holder = current[0] if current[0] else "unknown"
                return {"error": f"Job already claimed by {holder}"}
            return {"error": f"Job not found: {job_id}"}

    # Notify UI clients
    _emit_jobs_update()

    return {"claimed": True, "job_id": job_id, "agent": agent_id}


def get_or_create_system_job(name: str, system_tag: str) -> dict:
    """Get or create a system container job (Agents or Projects).

    Args:
        name: Display name for the job
        system_tag: Tag to identify this system job (e.g., "system:agents")

    Returns:
        The system job dict
    """
    all_jobs = list_jobs()
    now = datetime.utcnow().isoformat() + "Z"

    # Find existing system job by tag at root level
    for job in all_jobs:
        if system_tag in job.get("tags", []) and job["parent_id"] is None:
            return job

    # PROTECTION: Check if there's a system container that was moved or has corrupted tags
    # Look for jobs by name that should be system containers
    for job in all_jobs:
        if job["name"] == name:
            job_tags = job.get("tags", []) or []
            needs_repair = False
            repairs = []

            # Check if tags are missing/corrupted
            if system_tag not in job_tags:
                needs_repair = True
                repairs.append(f"restoring tag '{system_tag}'")

            # Check if it was moved from root level
            if job["parent_id"] is not None:
                needs_repair = True
                repairs.append("moving back to root level")

            if needs_repair:
                print(f"WARNING: Repairing system container '{name}' (id={job['id']}): {', '.join(repairs)}")
                # Repair the container
                new_tags = list(set(job_tags + [system_tag]))
                with _transaction() as conn:
                    conn.execute(
                        "UPDATE jobs SET parent_id = NULL, tags = ?, updated_at = ? WHERE id = ?",
                        (json.dumps(new_tags), now, job["id"])
                    )
                # Notify UI of the repair
                _emit_jobs_update()
                return _load_job(job["id"])

    # Create new system job
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    with _transaction() as conn:
        conn.execute('''
            INSERT INTO jobs (id, name, parent_id, status, created_at, updated_at,
                            created_by, description, tags)
            VALUES (?, ?, NULL, 'todo', ?, ?, 'system', ?, ?)
        ''', (
            job_id, name, now, now,
            f"System container for {name.lower()}",
            json.dumps([system_tag])
        ))

    print(f"Created system job: {name}")
    return _load_job(job_id)


def get_agents_container() -> dict:
    """Get or create the Agents container job."""
    return get_or_create_system_job("Agents", "system:agents")


def get_projects_container() -> dict:
    """Get or create the Projects container job."""
    return get_or_create_system_job("Projects", "system:projects")


def get_system_container() -> dict:
    """Get or create the System container job for system-generated jobs."""
    return get_or_create_system_job("System", "system:system")


def sync_agent_inbox_jobs():
    """Sync agent inbox jobs with current agents.

    Creates inbox jobs for new agents under the Agents container,
    archives orphaned ones, and updates names if agents were renamed.
    Also migrates any orphaned user jobs under Projects.
    """
    from ..agents.agents import list_agents

    # Ensure system containers exist
    agents_container = get_agents_container()
    projects_container = get_projects_container()
    system_container = get_system_container()

    agents = list_agents()
    agent_ids = {a["id"] for a in agents}
    agent_names = {a["id"]: a.get("name", a["id"]) for a in agents}

    all_jobs = list_jobs()
    now = datetime.utcnow().isoformat() + "Z"
    changes_made = False

    # Get existing agent inbox jobs (jobs with agent_id set)
    inbox_jobs = {j["agent_id"]: j for j in all_jobs if j.get("agent_id")}

    # Create inbox jobs for agents that don't have one
    for agent in agents:
        agent_id = agent["id"]
        agent_name = agent.get("name", agent_id)

        if agent_id not in inbox_jobs:
            # Create new inbox job under Agents container
            job_id = f"job-{uuid.uuid4().hex[:8]}"
            with _transaction() as conn:
                conn.execute('''
                    INSERT INTO jobs (id, name, parent_id, status, created_at, updated_at,
                                    created_by, description, tags, agent_id)
                    VALUES (?, ?, ?, 'todo', ?, ?, 'system', ?, ?, ?)
                ''', (
                    job_id, agent_name, agents_container["id"], now, now,
                    f"Inbox for {agent_name}",
                    json.dumps(["agent-inbox"]),
                    agent_id
                ))
            print(f"Created inbox job for agent: {agent_id}")
            changes_made = True

        else:
            job = inbox_jobs[agent_id]
            updates_needed = []

            # Check if name changed
            if job["name"] != agent_name:
                updates_needed.append(("name", agent_name))
                updates_needed.append(("description", f"Inbox for {agent_name}"))

            # Check if needs to be moved under Agents container
            if job["parent_id"] != agents_container["id"]:
                updates_needed.append(("parent_id", agents_container["id"]))

            if updates_needed:
                set_clauses = ", ".join(f"{k} = ?" for k, v in updates_needed)
                values = [v for k, v in updates_needed] + [now, job["id"]]
                with _transaction() as conn:
                    conn.execute(
                        f"UPDATE jobs SET {set_clauses}, updated_at = ? WHERE id = ?",
                        values
                    )
                print(f"Updated inbox job for agent: {agent_id}")
                changes_made = True

    # Archive inbox jobs for deleted agents
    for agent_id, job in inbox_jobs.items():
        if agent_id not in agent_ids and job["status"] != "archived":
            with _transaction() as conn:
                conn.execute(
                    "UPDATE jobs SET status = 'archived', updated_at = ? WHERE id = ?",
                    (now, job["id"])
                )
            print(f"Archived inbox job for deleted agent: {agent_id}")
            changes_made = True

    # Migrate orphaned root jobs (user-created, not system) under Projects
    system_tags = {"system:agents", "system:projects", "system:system"}
    system_container_names = {"Agents", "Projects", "System"}
    for job in all_jobs:
        # Skip if not a root job
        if job["parent_id"] is not None:
            continue

        # Skip if it's a system container (check by tag)
        if any(tag in system_tags for tag in job.get("tags", [])):
            continue

        # PROTECTION: Also skip if job name matches system container names
        # This prevents moving containers with corrupted/missing tags
        if job["name"] in system_container_names:
            # Log warning about potential tag corruption
            job_tags = job.get("tags", [])
            if not any(tag in system_tags for tag in job_tags):
                print(f"WARNING: System container '{job['name']}' (id={job['id']}) has corrupted tags: {job_tags}")
                print(f"  Expected one of: {system_tags}")
                print(f"  Skipping migration and preserving as root job")
            continue

        # Skip agent inbox jobs (handled above)
        if job.get("agent_id"):
            continue

        # This is a user root job - move it under Projects
        with _transaction() as conn:
            conn.execute(
                "UPDATE jobs SET parent_id = ?, updated_at = ? WHERE id = ?",
                (projects_container["id"], now, job["id"])
            )
        print(f"Moved job '{job['name']}' under Projects")
        changes_made = True

    if changes_made:
        _emit_jobs_update()

    return {"synced": True, "agent_count": len(agents)}


@tool("release_job", "Release a claimed job. Use when: done working or need to let another agent take over.", tool_type="data")
def release_job(job_id: str, agent_id: str) -> dict:
    """Release a job after working on it.

    Resets status from 'working' back to 'todo' so another agent can claim it.

    Args:
        job_id: The job to release
        agent_id: The agent releasing the job
    """
    now = datetime.utcnow().isoformat() + "Z"
    with _transaction() as conn:
        # Reset status to 'todo' and clear in_progress_by
        conn.execute(
            "UPDATE jobs SET in_progress_by = NULL, status = 'todo', updated_at = ? WHERE id = ? AND in_progress_by = ?",
            (now, job_id, agent_id)
        )

    # Notify UI clients
    _emit_jobs_update()

    return {"released": True, "job_id": job_id}


@tool("error_job", "Mark a job as failed with an error. Use when: job cannot be completed due to an error.", tool_type="data")
def error_job(job_id: str, error_message: str, agent: str = "user") -> Optional[dict]:
    """Mark a job as failed with an error.

    Args:
        job_id: The job to mark as error
        error_message: Description of what went wrong
        agent: Who is marking the error
    """
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        conn.execute('''
            UPDATE jobs SET status = 'error', in_progress_by = NULL, updated_at = ?
            WHERE id = ?
        ''', (now, job_id))

        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, ?)
        ''', (job_id, now, agent, f"error: {error_message}"))

    # Emit job:error to each assignee
    for assignee in job.get("assignees", []):
        _emit_event("job:error", scope=assignee, data={"job_id": job_id, "name": job["name"], "error": error_message})

    # Notify UI clients
    _emit_jobs_update()

    return _load_job(job_id)


# =============================================================================
# AGENT QUERY FUNCTIONS (non-tool helpers for API)
# =============================================================================

def get_jobs_completed_by_agent(agent_id: str, limit: int = 20) -> List[dict]:
    """Get jobs that were completed by a specific agent.

    Queries the job_logs table for 'completed' actions by the given agent,
    then loads the full job records.

    Args:
        agent_id: The agent ID to query
        limit: Maximum number of jobs to return (default 20)

    Returns:
        List of job dicts, most recently completed first
    """
    conn = _get_connection()
    cursor = conn.execute('''
        SELECT DISTINCT jl.job_id, jl.timestamp
        FROM job_logs jl
        WHERE jl.agent = ? AND jl.action = 'completed'
        ORDER BY jl.timestamp DESC
        LIMIT ?
    ''', (agent_id, limit))

    jobs = []
    for row in cursor:
        job = _load_job(row["job_id"])
        if job:
            jobs.append(job)

    return jobs
