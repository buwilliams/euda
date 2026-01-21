"""
Jobs API Routes
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...llms.tools.data.jobs import (
    list_jobs, get_job, create_job, update_job,
    complete_job, restore_job, archive_job, add_job_log, get_child_jobs, delete_job,
    assign_agent, unassign_agent, list_assignees, handoff_job, unblock_job
)
from ...llms.tools.data.assets import list_assets, read_asset, write_asset, delete_asset


router = APIRouter()


class CreateJobRequest(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    tags: Optional[List[str]] = None
    assignees: Optional[List[str]] = None
    due_date: Optional[str] = None
    someday: bool = False


class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    assignees: Optional[List[str]] = None
    due_date: Optional[str] = None
    someday: Optional[bool] = None


class AssignAgentRequest(BaseModel):
    agent_id: str


class AddLogRequest(BaseModel):
    action: str
    agent: str = "user"


class JobFeedbackRequest(BaseModel):
    message: str


class WriteAssetRequest(BaseModel):
    content: str


@router.get("")
def api_list_jobs(status: Optional[str] = None, parent_id: Optional[str] = None, assignee: Optional[str] = None):
    """List all jobs with optional filters."""
    return list_jobs(status=status, parent_id=parent_id, assignee=assignee)


@router.get("/{job_id}")
def api_get_job(job_id: str):
    """Get a job by ID."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("")
def api_create_job(request: CreateJobRequest):
    """Create a new job."""
    return create_job(
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
        tags=request.tags,
        assignees=request.assignees,
        due_date=request.due_date,
        someday=request.someday
    )


@router.patch("/{job_id}")
def api_update_job(job_id: str, request: UpdateJobRequest):
    """Update a job."""
    result = update_job(
        job_id=job_id,
        name=request.name,
        description=request.description,
        status=request.status,
        tags=request.tags,
        assignees=request.assignees,
        due_date=request.due_date,
        someday=request.someday
    )
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{job_id}/complete")
def api_complete_job(job_id: str):
    """Mark a job as completed."""
    result = complete_job(job_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{job_id}/archive")
def api_archive_job(job_id: str):
    """Archive a job."""
    result = archive_job(job_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{job_id}/restore")
def api_restore_job(job_id: str):
    """Restore a completed job back to todo."""
    result = restore_job(job_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{job_id}/unblock")
def api_unblock_job(job_id: str):
    """Remove blocking tags (waiting:*, blocked:*) from a job.

    This puts the job back in agents' work queues.
    """
    was_blocked = unblock_job(job_id)
    if was_blocked:
        return {"status": "unblocked", "job_id": job_id}
    return {"status": "not_blocked", "job_id": job_id}


@router.delete("/{job_id}")
def api_delete_job(job_id: str, delete_children: bool = False):
    """Delete a job permanently."""
    result = delete_job(job_id, delete_children=delete_children)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{job_id}/log")
def api_add_log(job_id: str, request: AddLogRequest):
    """Add a log entry to a job."""
    result = add_job_log(job_id, request.action, request.agent)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{job_id}/feedback")
def api_job_feedback(job_id: str, request: JobFeedbackRequest):
    """Send feedback about a job to the appropriate agent.

    Routes to:
    1. pending_from agent (if job was handed off to user)
    2. First assignee (if job is assigned to an agent)
    3. Chat agent (fallback for routing)
    """
    # User providing feedback means they're engaging - unblock if blocked
    unblock_job(job_id)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Determine target agent
    target_agent = None

    # First check pending_from (who handed it to us)
    if job.get("pending_from") and job["pending_from"] != "user":
        target_agent = job["pending_from"]

    # Otherwise check current assignees for an agent
    if not target_agent and job.get("assignees"):
        agents = [a for a in job["assignees"] if a != "user"]
        if agents:
            target_agent = agents[0]

    # Fallback to chat for routing
    if not target_agent:
        target_agent = "chat"

    # Append feedback to job description
    current_desc = job.get("description") or ""
    new_desc = f"{current_desc}\n\n---\n**User Feedback:** {request.message}"
    update_job(job_id, description=new_desc)

    # Hand off to agent
    result = handoff_job(job_id, target_agent, f"User feedback: {request.message}", agent="user")

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"status": "sent", "to_agent": target_agent, "job_id": job_id}


@router.get("/{job_id}/children")
def api_get_children(job_id: str):
    """Get child jobs."""
    return get_child_jobs(job_id)


@router.get("/{job_id}/api-calls")
def api_get_job_api_calls(job_id: str, days: int = 7):
    """Get API calls made for this job.

    Args:
        job_id: ID of the job
        days: Number of days to look back (default 7)

    Returns:
        Dict with call count, total cost, and list of API calls
    """
    from ...agent.cognition.metacognition import get_calls_by_job, get_job_call_count

    summary = get_job_call_count(job_id, days)
    calls = get_calls_by_job(job_id, days)

    return {
        **summary,
        "calls": calls
    }


# Assignment endpoints

@router.get("/{job_id}/assignees")
def api_list_assignees(job_id: str):
    """List agents assigned to a job."""
    result = list_assignees(job_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{job_id}/assign")
def api_assign_agent(job_id: str, request: AssignAgentRequest):
    """Assign an agent to a job."""
    result = assign_agent(job_id, request.agent_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{job_id}/unassign")
def api_unassign_agent(job_id: str, request: AssignAgentRequest):
    """Remove an agent from a job."""
    result = unassign_agent(job_id, request.agent_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# Asset endpoints

@router.get("/{job_id}/assets")
def api_list_assets(job_id: str):
    """List assets for a job."""
    return list_assets(job_id)


@router.get("/{job_id}/assets/{filename}")
def api_get_asset(job_id: str, filename: str):
    """Get an asset."""
    result = read_asset(job_id, filename)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{job_id}/assets/{filename}")
def api_write_asset(job_id: str, filename: str, request: WriteAssetRequest):
    """Write an asset."""
    # User editing an asset signals they're working on this job - unblock it
    unblock_job(job_id)
    return write_asset(job_id, filename, request.content)


@router.delete("/{job_id}/assets/{filename}")
def api_delete_asset(job_id: str, filename: str):
    """Delete an asset."""
    result = delete_asset(job_id, filename)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Job execution trace endpoint
@router.get("/{job_id}/trace")
def api_get_job_trace(job_id: str, days: int = 7):
    """Get execution trace for a job.

    Combines:
    - Job logs from database (actions taken)
    - API calls from cost tracker (LLM interactions)

    Returns a chronological timeline of events.
    """
    from ...agent.cognition.metacognition import get_calls_by_job

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get job logs from database
    from ...llms.tools.data.jobs import get_job_logs
    job_logs = get_job_logs(job_id)

    # Get API calls
    api_calls = get_calls_by_job(job_id, days)

    # Normalize entries into a common trace format
    entries = []

    # Add job logs
    for log in job_logs:
        entries.append({
            "timestamp": log.get("timestamp"),
            "event": "action",
            "agent": log.get("agent"),
            "details": {
                "action": log.get("action")
            }
        })

    # Add API calls (LLM interactions)
    for call in api_calls:
        entries.append({
            "timestamp": call.get("timestamp"),
            "event": "llm_call",
            "agent": call.get("agent"),
            "details": {
                "model": call.get("model"),
                "input_tokens": call.get("input_tokens"),
                "output_tokens": call.get("output_tokens"),
                "cost": call.get("cost")
            }
        })

    # Sort by timestamp (oldest first for timeline)
    entries.sort(key=lambda x: x.get("timestamp", ""))

    # Calculate summary stats
    total_cost = sum(e.get("details", {}).get("cost", 0) for e in entries if e.get("event") == "llm_call")
    llm_calls = sum(1 for e in entries if e.get("event") == "llm_call")
    actions = sum(1 for e in entries if e.get("event") == "action")

    return {
        "job_id": job_id,
        "job_name": job.get("name"),
        "summary": {
            "llm_calls": llm_calls,
            "actions": actions,
            "total_cost": round(total_cost, 4)
        },
        "entries": entries
    }
