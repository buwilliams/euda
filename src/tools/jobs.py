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


# Initialize schema on module import
_ensure_schema()


def _row_to_job(row: sqlite3.Row, logs: List[dict] = None) -> dict:
    """Convert a database row to a job dictionary."""
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


@tool("list_jobs", "List all jobs, optionally filtered by status or parent")
def list_jobs(status: str = None, parent_id: str = None) -> List[dict]:
    """List jobs with optional filters."""
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
                            created_by, description, due_date, someday, tags)
            VALUES (?, ?, ?, 'todo', ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_id, name, parent_id, now, now, created_by,
            description, due_date, int(someday), json.dumps(tags or [])
        ))

        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'created')
        ''', (job_id, now, created_by))

    return _load_job(job_id)


@tool("update_job", "Update a job's fields")
def update_job(
    job_id: str,
    name: str = None,
    description: str = None,
    status: str = None,
    tags: list = None,
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
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date if due_date else None)  # Empty string means clear
    if someday is not None:
        updates.append("someday = ?")
        params.append(int(someday))

    params.append(job_id)

    with _transaction() as conn:
        conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params)

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
