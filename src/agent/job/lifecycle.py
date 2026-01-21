"""
Job Lifecycle - Job state machine and transitions.

Job States:
- pending: Job is waiting to be processed
- working: Job is being processed by an agent
- done: Job completed successfully
- error: Job failed with an error

State Transitions:
- pending → working (agent claims job)
- working → done (success)
- working → error (failure)
- done → pending (restore)
- error → pending (retry)
"""

from enum import Enum
from typing import Optional
from datetime import datetime


class JobState(Enum):
    """Job execution states."""
    PENDING = "pending"
    WORKING = "working"
    DONE = "done"
    ERROR = "error"


def claim_job(job_id: str, agent_id: str) -> bool:
    """Claim a job for processing (pending → working).

    Args:
        job_id: The job to claim
        agent_id: The agent claiming the job

    Returns:
        True if job was claimed, False if already claimed or not found
    """
    from ...tools.data.jobs import get_job, _update_job, _get_connection

    job = get_job(job_id)
    if not job:
        return False

    # Only claim pending jobs
    if job.get("status") != "todo":
        return False

    # Update status to working (using internal fields)
    with _get_connection() as conn:
        now = datetime.utcnow().isoformat() + "Z"
        conn.execute('''
            UPDATE jobs
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', ("working", now, job_id))

        # Log the claim
        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'claimed')
        ''', (job_id, now, agent_id))

    return True


def complete_job(job_id: str, agent_id: str) -> bool:
    """Complete a job (working → done).

    Args:
        job_id: The job to complete
        agent_id: The agent completing the job

    Returns:
        True if job was completed, False otherwise
    """
    from ...tools.data.jobs import complete_job as tools_complete_job

    result = tools_complete_job(job_id, agent=agent_id)
    return result is not None and "error" not in result


def fail_job(job_id: str, agent_id: str, error: str) -> bool:
    """Mark a job as failed (working → error).

    Args:
        job_id: The job that failed
        agent_id: The agent that encountered the error
        error: Error description

    Returns:
        True if job was marked as error, False otherwise
    """
    from ...tools.data.jobs import get_job, _get_connection

    job = get_job(job_id)
    if not job:
        return False

    with _get_connection() as conn:
        now = datetime.utcnow().isoformat() + "Z"
        conn.execute('''
            UPDATE jobs
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', ("error", now, job_id))

        # Log the error
        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action, details)
            VALUES (?, ?, ?, 'error', ?)
        ''', (job_id, now, agent_id, error))

    return True


def release_job(job_id: str, agent_id: str) -> bool:
    """Release a claimed job back to pending (working → pending).

    Args:
        job_id: The job to release
        agent_id: The agent releasing the job

    Returns:
        True if job was released, False otherwise
    """
    from ...tools.data.jobs import get_job, _get_connection

    job = get_job(job_id)
    if not job:
        return False

    # Only release working jobs
    if job.get("status") != "working":
        return False

    with _get_connection() as conn:
        now = datetime.utcnow().isoformat() + "Z"
        conn.execute('''
            UPDATE jobs
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', ("todo", now, job_id))

        # Log the release
        conn.execute('''
            INSERT INTO job_logs (job_id, timestamp, agent, action)
            VALUES (?, ?, ?, 'released')
        ''', (job_id, now, agent_id))

    return True


def get_pending_jobs(agent_id: str, limit: int = 10) -> list:
    """Get pending jobs assigned to an agent.

    Args:
        agent_id: The agent's ID
        limit: Maximum number of jobs to return

    Returns:
        List of job dicts
    """
    from ...tools.data.jobs import list_jobs

    result = list_jobs(
        status="todo",
        assignee=agent_id,
        limit=limit
    )
    return result if isinstance(result, list) else []
