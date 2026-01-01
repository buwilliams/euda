"""
Task management routes for Euno web API.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...tools.worker.task import (
    create_task, create_learning_task, get_tasks_data, get_task,
    get_daily_view, add_quick_task, update_task_status, delete_task,
    get_recent_results, get_result, get_completed_tasks_data, archive_task,
    update_task_when
)


router = APIRouter(prefix="/api", tags=["tasks"])


class TaskRequest(BaseModel):
    description: str
    task_type: str = "general"
    project_id: Optional[str] = None
    priority: str = "normal"
    due_date: Optional[str] = None


class LearningTaskRequest(BaseModel):
    description: str
    project_id: Optional[str] = None
    learning_objectives: Optional[list] = None
    preferred_format: str = "mixed"


class QuickTaskRequest(BaseModel):
    description: str


class TaskStatusRequest(BaseModel):
    status: str


class TaskArchiveRequest(BaseModel):
    reason: str = ""
    outcome: str = "abandoned"  # completed, abandoned, deferred, superseded


class WhenRequest(BaseModel):
    when_type: str  # "today", "date", "someday", "anytime", "clear"
    date: Optional[str] = None  # For "date" type, ISO format YYYY-MM-DD


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50
):
    """Get tasks with optional filters."""
    tasks = get_tasks_data(
        status=status,
        project_id=project_id,
        priority=priority,
        limit=limit
    )
    return {"tasks": tasks}


@router.get("/tasks/daily")
async def get_todays_tasks(date: Optional[str] = None):
    """Get daily task view."""
    content = get_daily_view(date)
    return {"content": content}


@router.get("/tasks/completed")
async def get_completed_tasks(days: int = 30, limit: int = 50):
    """Get recently completed tasks."""
    tasks = get_completed_tasks_data(days=days, limit=limit)
    return {"tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_task_details(task_id: str):
    """Get task details."""
    content = get_task(task_id)
    return {"content": content}


@router.post("/tasks")
async def create_new_task(request: TaskRequest):
    """Create a new task."""
    result = create_task(
        description=request.description,
        task_type=request.task_type,
        project_id=request.project_id,
        priority=request.priority,
        due_date=request.due_date,
        source_agent="api"
    )
    return {"status": "success", "message": result}


@router.post("/tasks/learning")
async def create_new_learning_task(request: LearningTaskRequest):
    """Create a learning task."""
    result = create_learning_task(
        description=request.description,
        project_id=request.project_id,
        learning_objectives=request.learning_objectives,
        preferred_format=request.preferred_format
    )
    return {"status": "success", "message": result}


@router.post("/tasks/quick")
async def add_new_quick_task(request: QuickTaskRequest):
    """Add a quick ad-hoc task for today."""
    result = add_quick_task(request.description)
    return {"status": "success", "message": result}


@router.put("/tasks/{task_id}/status")
async def update_task_status_endpoint(task_id: str, request: TaskStatusRequest):
    """Update task status."""
    result = update_task_status(task_id, request.status)
    return {"status": "success", "message": result}


@router.delete("/tasks/{task_id}")
async def delete_task_endpoint(task_id: str):
    """Delete a task."""
    result = delete_task(task_id)
    return {"status": "success", "message": result}


@router.post("/tasks/{task_id}/archive")
async def archive_task_endpoint(task_id: str, request: TaskArchiveRequest = None):
    """Archive a task with behavioral context."""
    if request:
        result = archive_task(task_id, reason=request.reason, outcome=request.outcome)
    else:
        result = archive_task(task_id)
    return {"status": "success", "message": result}


@router.put("/tasks/{task_id}/when")
async def update_task_when_endpoint(task_id: str, request: WhenRequest):
    """
    Update task's "when" scheduling (Things-like).

    when_type options:
    - "today": Set due_date to today
    - "date": Set due_date to provided date
    - "someday": Clear due_date, set someday=true
    - "anytime": Clear due_date, set someday=false
    - "clear": Clear due_date, set someday=false (same as anytime)
    """
    result = update_task_when(task_id, request.when_type, request.date)
    if "not found" in result.lower():
        raise HTTPException(status_code=404, detail=result)
    return {"status": "success", "message": result}


@router.get("/results")
async def list_results(project_id: Optional[str] = None, limit: int = 10):
    """Get recent results."""
    content = get_recent_results(project_id=project_id, limit=limit)
    return {"content": content}


@router.get("/results/{result_id}")
async def get_result_details(result_id: str):
    """Get result details."""
    content = get_result(result_id)
    return {"content": content}
