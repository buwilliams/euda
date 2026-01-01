"""
Job Tools - CRUD operations for jobs.

Jobs are the primary unit of work in the system.
They can be nested via parent_id to form hierarchies.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from . import tool


DATA_DIR = Path(__file__).parent.parent.parent / "data"
JOBS_DIR = DATA_DIR / "jobs"


def _ensure_jobs_dir():
    """Ensure jobs directory exists."""
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _load_job(job_id: str) -> Optional[dict]:
    """Load a job by ID."""
    path = JOBS_DIR / f"{job_id}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def _save_job(job: dict):
    """Save a job to disk."""
    _ensure_jobs_dir()
    path = JOBS_DIR / f"{job['id']}.json"
    with open(path, "w") as f:
        json.dump(job, f, indent=2)


@tool("list_jobs", "List all jobs, optionally filtered by status or parent")
def list_jobs(status: str = None, parent_id: str = None) -> List[dict]:
    """List jobs with optional filters."""
    _ensure_jobs_dir()

    jobs = []
    for path in JOBS_DIR.glob("*.json"):
        with open(path) as f:
            job = json.load(f)

            # Apply filters
            if status and job.get("status") != status:
                continue
            if parent_id is not None:
                if parent_id == "" and job.get("parent_id") is not None:
                    continue  # Want top-level only
                elif parent_id and job.get("parent_id") != parent_id:
                    continue

            jobs.append(job)

    # Sort by updated_at descending
    jobs.sort(key=lambda j: j.get("updated_at", ""), reverse=True)
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
    created_by: str = "user"
) -> dict:
    """Create a new job."""
    now = datetime.utcnow().isoformat() + "Z"

    job = {
        "id": f"job-{uuid.uuid4().hex[:8]}",
        "name": name,
        "parent_id": parent_id,
        "status": "todo",
        "created_at": now,
        "updated_at": now,
        "created_by": created_by,
        "description": description,
        "due_date": due_date,
        "tags": tags or [],
        "log": [
            {
                "timestamp": now,
                "agent": created_by,
                "action": "created"
            }
        ]
    }

    _save_job(job)
    return job


@tool("update_job", "Update a job's fields")
def update_job(
    job_id: str,
    name: str = None,
    description: str = None,
    status: str = None,
    tags: list = None,
    due_date: str = None
) -> Optional[dict]:
    """Update a job's fields."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    # Update provided fields
    if name is not None:
        job["name"] = name
    if description is not None:
        job["description"] = description
    if status is not None:
        job["status"] = status
    if tags is not None:
        job["tags"] = tags
    if due_date is not None:
        job["due_date"] = due_date

    job["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save_job(job)
    return job


@tool("complete_job", "Mark a job as completed")
def complete_job(job_id: str, agent: str = "user") -> Optional[dict]:
    """Mark a job as completed."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    now = datetime.utcnow().isoformat() + "Z"
    job["status"] = "completed"
    job["updated_at"] = now
    job["log"].append({
        "timestamp": now,
        "agent": agent,
        "action": "completed"
    })

    _save_job(job)
    return job


@tool("archive_job", "Archive a job (mark as no longer relevant)")
def archive_job(job_id: str, agent: str = "user") -> Optional[dict]:
    """Archive a job."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    now = datetime.utcnow().isoformat() + "Z"
    job["status"] = "archived"
    job["updated_at"] = now
    job["log"].append({
        "timestamp": now,
        "agent": agent,
        "action": "archived"
    })

    _save_job(job)
    return job


@tool("add_job_log", "Add a log entry to a job")
def add_job_log(job_id: str, action: str, agent: str = "user") -> Optional[dict]:
    """Add a log entry to a job."""
    job = _load_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}

    now = datetime.utcnow().isoformat() + "Z"
    job["updated_at"] = now
    job["log"].append({
        "timestamp": now,
        "agent": agent,
        "action": action
    })

    _save_job(job)
    return job


@tool("get_child_jobs", "Get all child jobs of a parent job")
def get_child_jobs(parent_id: str) -> List[dict]:
    """Get all child jobs of a given parent."""
    return list_jobs(parent_id=parent_id)
