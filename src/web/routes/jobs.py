"""
Jobs API Routes
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...tools.jobs import (
    list_jobs, get_job, create_job, update_job,
    complete_job, restore_job, archive_job, add_job_log, get_child_jobs, delete_job
)
from ...tools.assets import list_assets, read_asset, write_asset, delete_asset


router = APIRouter()


class CreateJobRequest(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    tags: Optional[List[str]] = None
    due_date: Optional[str] = None
    someday: bool = False


class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    due_date: Optional[str] = None
    someday: Optional[bool] = None


class AddLogRequest(BaseModel):
    action: str
    agent: str = "user"


class WriteAssetRequest(BaseModel):
    content: str


@router.get("")
def api_list_jobs(status: Optional[str] = None, parent_id: Optional[str] = None):
    """List all jobs with optional filters."""
    return list_jobs(status=status, parent_id=parent_id)


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


@router.get("/{job_id}/children")
def api_get_children(job_id: str):
    """Get child jobs."""
    return get_child_jobs(job_id)


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
    return write_asset(job_id, filename, request.content)


@router.delete("/{job_id}/assets/{filename}")
def api_delete_asset(job_id: str, filename: str):
    """Delete an asset."""
    result = delete_asset(job_id, filename)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
