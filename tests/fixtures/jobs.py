"""
Job test fixtures and factories.
"""

from typing import Optional, List
from datetime import datetime


def create_test_job(
    name: str = "Test Job",
    description: str = None,
    status: str = "todo",
    tags: List[str] = None,
    assignees: List[str] = None,
    due_date: str = None,
    someday: bool = False,
    parent_id: str = None,
    created_by: str = "user",
    **overrides
) -> dict:
    """Create a job dictionary for testing (does NOT persist to database).

    For actual database operations, use the create_job tool directly.

    Args:
        name: Job name
        description: Job description
        status: Job status (todo, completed, archived)
        tags: List of tags
        assignees: List of agent IDs assigned to this job
        due_date: Due date (YYYY-MM-DD)
        someday: Whether this is a someday/maybe job
        parent_id: Parent job ID
        created_by: Who created the job
        **overrides: Additional fields

    Returns:
        Job dictionary (not persisted)
    """
    now = datetime.utcnow().isoformat() + "Z"

    job = {
        "id": f"job-test-{name.lower().replace(' ', '-')[:8]}",
        "name": name,
        "description": description,
        "status": status,
        "tags": tags or [],
        "assignees": assignees or [],
        "due_date": due_date,
        "someday": someday,
        "parent_id": parent_id,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "in_progress_by": None,
        "agent_id": None,
        "pending_from": None,
        "log": []
    }
    job.update(overrides)
    return job


def create_job_with_tags(tags: List[str], **kwargs) -> dict:
    """Create a job with specific tags."""
    return create_test_job(tags=tags, **kwargs)


def create_waiting_job(waiting_for: str = "user", **kwargs) -> dict:
    """Create a job with a waiting:* tag."""
    return create_test_job(tags=[f"waiting:{waiting_for}"], **kwargs)


def create_blocked_job(blocked_by: str = "dependency", **kwargs) -> dict:
    """Create a job with a blocked:* tag."""
    return create_test_job(tags=[f"blocked:{blocked_by}"], **kwargs)


def create_someday_job(**kwargs) -> dict:
    """Create a someday/maybe job."""
    return create_test_job(someday=True, **kwargs)


def create_future_job(days_ahead: int = 7, **kwargs) -> dict:
    """Create a job with a future due date."""
    from datetime import date, timedelta
    future_date = (date.today() + timedelta(days=days_ahead)).isoformat()
    return create_test_job(due_date=future_date, **kwargs)


def create_assigned_job(agent_id: str = "test-agent", **kwargs) -> dict:
    """Create a job assigned to a specific agent."""
    return create_test_job(assignees=[agent_id], **kwargs)
