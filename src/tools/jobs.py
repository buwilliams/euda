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

from . import tool


DATA_DIR = Path(__file__).parent.parent.parent / "data"
JOBS_DIR = DATA_DIR / "jobs"
DB_PATH = JOBS_DIR / "db.sqlite"

# Thread-local storage for database connections
_local = threading.local()


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
            status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'completed', 'archived')),
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


# Initialize schema on module import
_ensure_schema()


def _wake_agent(agent_id: str):
    """Wake an agent if it exists and is running."""
    from ..manager import get_manager
    manager = get_manager()
    if manager:
        manager.wake_agent(agent_id)


def _row_to_job(row: sqlite3.Row, logs: List[dict] = None) -> dict:
    """Convert a database row to a job dictionary."""
    # Handle columns that may not exist in older schemas
    assignees_raw = row["assignees"] if "assignees" in row.keys() else None
    in_progress_by = row["in_progress_by"] if "in_progress_by" in row.keys() else None

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


@tool("list_jobs", "List all jobs, optionally filtered by status, parent, tag, or assignee")
def list_jobs(status: str = None, parent_id: str = None, tag: str = None, assignee: str = None) -> List[dict]:
    """List jobs with optional filters.

    Args:
        status: Filter by status (todo, completed, archived)
        parent_id: Filter by parent job ID (empty string for root jobs)
        tag: Filter to jobs containing this tag
        assignee: Filter to jobs assigned to this agent ID
    """
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

    query += " ORDER BY updated_at DESC"

    cursor = conn.execute(query, params)
    jobs = []
    for row in cursor:
        logs = _get_job_logs(row["id"])
        jobs.append(_row_to_job(row, logs))

    return jobs


@tool("get_job", "Get a job by its ID")
def get_job(job_id: str) -> Optional[dict]:
    """Get a single job by ID."""
    return _load_job(job_id)


@tool("create_job", "Create a new job")
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
    """Create a new job."""
    now = datetime.utcnow().isoformat() + "Z"
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    with _transaction() as conn:
        conn.execute('''
            INSERT INTO jobs (id, name, parent_id, status, created_at, updated_at,
                            created_by, description, due_date, someday, tags, assignees)
            VALUES (?, ?, ?, 'todo', ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_id, name, parent_id, now, now, created_by,
            description, due_date, int(someday), json.dumps(tags or []),
            json.dumps(assignees or [])
        ))

        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'created')
        ''', (job_id, now, created_by))

    # Wake any assigned agents
    for agent_id in (assignees or []):
        _wake_agent(agent_id)

    return _load_job(job_id)


@tool("update_job", "Update a job's fields")
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

    # Wake any newly assigned agents
    if assignees is not None:
        old_assignees = set(job.get("assignees", []))
        new_assignees = set(assignees) - old_assignees
        for agent_id in new_assignees:
            _wake_agent(agent_id)

    return _load_job(job_id)


@tool("complete_job", "Mark a job as completed")
def complete_job(job_id: str, agent: str = "user") -> Optional[dict]:
    """Mark a job as completed."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    now = datetime.utcnow().isoformat() + "Z"

    with _transaction() as conn:
        conn.execute('''
            UPDATE jobs SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE id = ?
        ''', (now, now, job_id))

        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'completed')
        ''', (job_id, now, agent))

    return _load_job(job_id)


@tool("restore_job", "Restore a completed job back to todo")
def restore_job(job_id: str, agent: str = "user") -> Optional[dict]:
    """Restore a completed job back to todo status."""
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

    return _load_job(job_id)


@tool("archive_job", "Archive a job (mark as no longer relevant)")
def archive_job(job_id: str, agent: str = "user") -> Optional[dict]:
    """Archive a job."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

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

    return _load_job(job_id)


@tool("add_job_log", "Add a log entry to a job")
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

    return _load_job(job_id)


@tool("get_child_jobs", "Get all child jobs of a parent job")
def get_child_jobs(parent_id: str) -> List[dict]:
    """Get all child jobs of a given parent."""
    return list_jobs(parent_id=parent_id)


@tool("delete_job", "Delete a job permanently")
def delete_job(job_id: str, delete_children: bool = False) -> dict:
    """Delete a job. Optionally delete child jobs too."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    # Delete children if requested (must do before parent due to FK)
    if delete_children:
        children = get_child_jobs(job_id)
        for child in children:
            delete_job(child["id"], delete_children=True)

    with _transaction() as conn:
        # Delete the job (logs cascade automatically via ON DELETE CASCADE)
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    return {"deleted": job_id, "children_deleted": delete_children}


@tool("assign_agent", "Assign an agent to a job")
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

    # Wake the agent
    _wake_agent(agent_id)

    return _load_job(job_id)


@tool("unassign_agent", "Remove an agent assignment from a job")
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

    return _load_job(job_id)


@tool("list_assignees", "List agents assigned to a job")
def list_assignees(job_id: str) -> list:
    """Get list of agent IDs assigned to a job.

    Args:
        job_id: The job to check
    """
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    return job.get("assignees", [])


@tool("list_available_agents", "List all agent IDs that can be assigned to jobs")
def list_available_agents() -> list:
    """Get list of all available agent IDs."""
    from .agents import list_agents
    agents = list_agents()
    return [a["id"] for a in agents]


@tool("claim_job", "Claim a job for exclusive work")
def claim_job(job_id: str, agent_id: str) -> dict:
    """Claim a job to work on it exclusively.

    Returns error if already claimed by another agent.

    Args:
        job_id: The job to claim
        agent_id: The agent claiming the job
    """
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    current_holder = job.get("in_progress_by")
    if current_holder and current_holder != agent_id:
        return {"error": f"Job already claimed by {current_holder}"}

    now = datetime.utcnow().isoformat() + "Z"
    with _transaction() as conn:
        conn.execute(
            "UPDATE jobs SET in_progress_by = ?, updated_at = ? WHERE id = ?",
            (agent_id, now, job_id)
        )

    return {"claimed": True, "job_id": job_id, "agent": agent_id}


@tool("release_job", "Release a claimed job")
def release_job(job_id: str, agent_id: str) -> dict:
    """Release a job after working on it.

    Args:
        job_id: The job to release
        agent_id: The agent releasing the job
    """
    now = datetime.utcnow().isoformat() + "Z"
    with _transaction() as conn:
        conn.execute(
            "UPDATE jobs SET in_progress_by = NULL, updated_at = ? WHERE id = ? AND in_progress_by = ?",
            (now, job_id, agent_id)
        )
    return {"released": True, "job_id": job_id}
