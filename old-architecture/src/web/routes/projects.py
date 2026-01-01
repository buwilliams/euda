"""
Project management routes for Euno web API.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...tools.worker.project import (
    create_project, get_projects_data, get_project, update_project,
    add_milestone, archive_project, delete_project, get_projects_with_deadlines,
    get_project_notes, get_project_notes_count, prepend_project_note,
    parse_notes_list, delete_note, update_project_when
)


router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectRequest(BaseModel):
    title: str
    description: str
    project_type: str = "goal"
    priority: str = "normal"
    deadline: Optional[str] = None
    review_frequency: str = "weekly"
    values_alignment: Optional[list] = None


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[str] = None


class MilestoneRequest(BaseModel):
    title: str
    target_date: Optional[str] = None


class ProjectArchiveRequest(BaseModel):
    reason: str = ""
    outcome: str = "completed"  # completed, abandoned, paused, superseded


class ProjectNoteRequest(BaseModel):
    title: str
    content: str
    note_type: str = "note"  # note, research, update, decision


class WhenRequest(BaseModel):
    when_type: str  # "today", "date", "someday", "anytime", "clear"
    date: Optional[str] = None


@router.get("")
async def list_projects(status: str = "active", project_type: Optional[str] = None):
    """Get projects."""
    projects = get_projects_data(status=status, project_type=project_type)
    return {"projects": projects}


@router.get("/deadlines")
async def get_upcoming_deadlines(days: int = 7):
    """Get projects with upcoming deadlines."""
    projects = get_projects_with_deadlines(days)
    return {"projects": projects, "days": days}


@router.get("/{project_id}")
async def get_project_details(project_id: str):
    """Get project details."""
    content = get_project(project_id)
    return {"content": content}


@router.post("")
async def create_new_project(request: ProjectRequest):
    """Create a new project."""
    result = create_project(
        title=request.title,
        description=request.description,
        project_type=request.project_type,
        priority=request.priority,
        deadline=request.deadline,
        review_frequency=request.review_frequency,
        values_alignment=request.values_alignment
    )
    return {"status": "success", "message": result}


@router.put("/{project_id}")
async def update_project_details(project_id: str, request: ProjectUpdateRequest):
    """Update a project."""
    result = update_project(
        project_id=project_id,
        title=request.title,
        description=request.description,
        status=request.status,
        priority=request.priority,
        deadline=request.deadline
    )
    return {"status": "success", "message": result}


@router.post("/{project_id}/milestones")
async def add_project_milestone(project_id: str, request: MilestoneRequest):
    """Add a milestone to a project."""
    result = add_milestone(project_id, request.title, request.target_date)
    return {"status": "success", "message": result}


@router.post("/{project_id}/archive")
async def archive_project_endpoint(project_id: str, request: ProjectArchiveRequest = None):
    """Archive a project with behavioral context."""
    if request:
        result = archive_project(project_id, reason=request.reason, outcome=request.outcome)
    else:
        result = archive_project(project_id)
    return {"status": "success", "message": result}


@router.get("/{project_id}/notes")
async def get_project_notes_endpoint(project_id: str):
    """Get project notes."""
    notes = get_project_notes(project_id)
    count = get_project_notes_count(project_id)
    return {"project_id": project_id, "notes": notes, "count": count}


@router.get("/{project_id}/notes/list")
async def get_project_notes_list_endpoint(project_id: str):
    """Get project notes as structured list for UI."""
    notes = parse_notes_list(project_id)
    return {"project_id": project_id, "notes": notes, "count": len(notes)}


@router.delete("/{project_id}/notes/{filename}")
async def delete_project_note_endpoint(project_id: str, filename: str):
    """Delete a specific note by filename."""
    result = delete_note(project_id, filename)
    if "not found" in result.lower():
        raise HTTPException(status_code=404, detail=result)
    return {"status": "success", "message": result}


@router.post("/{project_id}/notes")
async def add_project_note_endpoint(project_id: str, request: ProjectNoteRequest):
    """Add a note to a project."""
    result = prepend_project_note(
        project_id=project_id,
        title=request.title,
        content=request.content,
        note_type=request.note_type
    )
    return {"status": "success", "message": result}


@router.post("/{project_id}/complete")
async def complete_project_endpoint(project_id: str):
    """Mark a project as completed."""
    result = update_project(project_id, status="completed")
    return {"status": "success", "message": result}


@router.delete("/{project_id}")
async def delete_project_endpoint(project_id: str, delete_tasks: bool = True):
    """Delete a project and optionally its associated tasks."""
    result = delete_project(project_id, delete_tasks=delete_tasks)
    return {"status": "success", "message": result}


@router.put("/{project_id}/when")
async def update_project_when_endpoint(project_id: str, request: WhenRequest):
    """
    Update project's "when" scheduling (Things-like).

    when_type options:
    - "today": Set deadline to today
    - "date": Set deadline to provided date
    - "someday": Clear deadline, set someday=true
    - "anytime": Clear deadline, set someday=false
    - "clear": Clear deadline, set someday=false (same as anytime)
    """
    result = update_project_when(project_id, request.when_type, request.date)
    if "not found" in result.lower():
        raise HTTPException(status_code=404, detail=result)
    return {"status": "success", "message": result}
