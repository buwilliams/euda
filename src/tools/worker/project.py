"""
Project management tools for annual planning.

Projects are ongoing goals that span days/weeks/months (e.g., "Learn Spanish", "Health goals").
Each project contains milestones and can have tasks associated with it.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Base paths - Projects are owned by Worker agent
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
WORKER_DIR = DATA_DIR / "worker"
PROJECTS_DIR = WORKER_DIR / "state" / "projects"
ARCHIVE_DIR = WORKER_DIR / "state" / "archive"
NOTES_DIR = PROJECTS_DIR / "notes"

# Ensure directories exist
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
NOTES_DIR.mkdir(parents=True, exist_ok=True)

# The General project for miscellaneous tasks
GENERAL_PROJECT_ID = "project-general"

# System projects for Euno-generated content
NOTIFICATIONS_PROJECT_ID = "project-notifications"
RECOMMENDATIONS_PROJECT_ID = "project-recommendations"

# All system project IDs (for filtering)
SYSTEM_PROJECT_IDS = {GENERAL_PROJECT_ID, NOTIFICATIONS_PROJECT_ID, RECOMMENDATIONS_PROJECT_ID}


def _generate_id() -> str:
    """Generate a unique project ID."""
    return f"project-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"


def _load_index() -> dict:
    """Load the projects index."""
    index_file = PROJECTS_DIR / "_index.json"
    if index_file.exists():
        with open(index_file, 'r') as f:
            return json.load(f)
    return {"projects": []}


def _save_index(index: dict):
    """Save the projects index."""
    index_file = PROJECTS_DIR / "_index.json"
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)


def _update_index(project: dict, remove: bool = False):
    """Update the index with a project entry."""
    index = _load_index()

    # Remove existing entry if present
    index["projects"] = [p for p in index["projects"] if p["id"] != project["id"]]

    if not remove:
        # Add updated entry
        index["projects"].append({
            "id": project["id"],
            "title": project["title"],
            "status": project["status"],
            "priority": project["priority"],
            "type": project["type"],
            "deadline": project.get("deadline"),
            "updated": project["updated"]
        })

    _save_index(index)


def ensure_general_project() -> str:
    """
    Ensure the General project exists for miscellaneous tasks.

    Returns:
        The General project ID
    """
    project_file = PROJECTS_DIR / f"{GENERAL_PROJECT_ID}.json"

    if project_file.exists():
        return GENERAL_PROJECT_ID

    # Create the General project
    now = datetime.now().isoformat()
    project = {
        "id": GENERAL_PROJECT_ID,
        "created": now,
        "updated": now,
        "title": "General",
        "description": "Miscellaneous tasks not associated with a specific goal",
        "type": "maintenance",
        "status": "active",
        "priority": "normal",
        "source": {
            "agent": "system",
            "context": "Auto-created for orphan tasks"
        },
        "milestones": [],
        "values_alignment": [],
        "deadline": None,
        "review_frequency": "weekly",
        "last_reviewed": None,
        "archived": False,
        "meta": {
            "total_tasks_created": 0,
            "tasks_completed": 0,
            "estimated_hours": 0,
            "logged_hours": 0
        }
    }

    with open(project_file, 'w') as f:
        json.dump(project, f, indent=2)

    _update_index(project)
    return GENERAL_PROJECT_ID


def ensure_notifications_project() -> str:
    """
    Ensure the Notifications project exists for system notifications.

    Returns:
        The Notifications project ID
    """
    project_file = PROJECTS_DIR / f"{NOTIFICATIONS_PROJECT_ID}.json"

    if project_file.exists():
        return NOTIFICATIONS_PROJECT_ID

    now = datetime.now().isoformat()
    project = {
        "id": NOTIFICATIONS_PROJECT_ID,
        "created": now,
        "updated": now,
        "title": "Notifications",
        "description": "System notifications and alerts from Euno",
        "type": "system",
        "status": "active",
        "priority": "normal",
        "source": {
            "agent": "system",
            "context": "System project for notifications"
        },
        "milestones": [],
        "values_alignment": [],
        "deadline": None,
        "someday": False,
        "review_frequency": "daily",
        "last_reviewed": None,
        "archived": False,
        "meta": {
            "total_tasks_created": 0,
            "tasks_completed": 0,
            "estimated_hours": 0,
            "logged_hours": 0
        }
    }

    with open(project_file, 'w') as f:
        json.dump(project, f, indent=2)

    _update_index(project)
    return NOTIFICATIONS_PROJECT_ID


def ensure_recommendations_project() -> str:
    """
    Ensure the Recommendations project exists for system recommendations.

    Returns:
        The Recommendations project ID
    """
    project_file = PROJECTS_DIR / f"{RECOMMENDATIONS_PROJECT_ID}.json"

    if project_file.exists():
        return RECOMMENDATIONS_PROJECT_ID

    now = datetime.now().isoformat()
    project = {
        "id": RECOMMENDATIONS_PROJECT_ID,
        "created": now,
        "updated": now,
        "title": "Curator",
        "description": "Curated suggestions from Euno based on your behaviors and interests",
        "type": "system",
        "status": "active",
        "priority": "normal",
        "source": {
            "agent": "system",
            "context": "System project for recommendations"
        },
        "milestones": [],
        "values_alignment": [],
        "deadline": None,
        "someday": False,
        "review_frequency": "weekly",
        "last_reviewed": None,
        "archived": False,
        "meta": {
            "total_tasks_created": 0,
            "tasks_completed": 0,
            "estimated_hours": 0,
            "logged_hours": 0
        }
    }

    with open(project_file, 'w') as f:
        json.dump(project, f, indent=2)

    _update_index(project)
    return RECOMMENDATIONS_PROJECT_ID


def is_system_project(project_id: str) -> bool:
    """Check if a project is a system project."""
    return project_id in SYSTEM_PROJECT_IDS


def get_project_title(project_id: str) -> str:
    """
    Get the title of a project by ID.

    Args:
        project_id: The project ID

    Returns:
        Project title or "Unknown" if not found
    """
    if not project_id:
        return "General"

    project_file = PROJECTS_DIR / f"{project_id}.json"
    if not project_file.exists():
        # Try archive
        project_file = ARCHIVE_DIR / f"{project_id}.json"

    if project_file.exists():
        with open(project_file, 'r') as f:
            project = json.load(f)
        return project.get("title", "Unknown")

    return "Unknown"


def _get_project_notes_dir(project_id: str) -> Path:
    """Get the notes directory for a project."""
    return NOTES_DIR / project_id


def get_project_notes(project_id: str) -> str:
    """
    Get all notes for a project as combined markdown.

    Args:
        project_id: The project ID

    Returns:
        Combined notes content, or empty string if none exist
    """
    notes = parse_notes_list(project_id)
    if not notes:
        return ""

    # Combine notes into markdown format
    parts = []
    for note in notes:
        header = f"## {note['date']} - {note['type']}: {note['title']}"
        parts.append(f"{header}\n\n{note['content']}")

    return "\n\n---\n\n".join(parts)


def get_project_notes_count(project_id: str) -> int:
    """
    Get the number of notes for a project.

    Args:
        project_id: The project ID

    Returns:
        Number of note files
    """
    notes_dir = _get_project_notes_dir(project_id)
    if not notes_dir.exists():
        return 0
    return len([f for f in notes_dir.iterdir() if f.suffix == '.md'])


def parse_notes_list(project_id: str) -> list:
    """
    Get project notes as a structured list.

    Args:
        project_id: The project ID

    Returns:
        List of note dictionaries with filename, date, title, content, preview
    """
    import re

    notes_dir = _get_project_notes_dir(project_id)
    if not notes_dir.exists():
        return []

    notes = []
    # Sort by filename descending (newest first since filenames are timestamps)
    note_files = sorted(notes_dir.glob("*.md"), reverse=True)

    for note_file in note_files:
        content = note_file.read_text()

        # Parse YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                body = parts[2].strip()

                # Parse frontmatter fields
                date = ""
                note_type = "Note"
                title = note_file.stem

                for line in frontmatter.split('\n'):
                    if line.startswith('date:'):
                        date = line[5:].strip()
                    elif line.startswith('type:'):
                        note_type = line[5:].strip()
                    elif line.startswith('title:'):
                        title = line[6:].strip()
            else:
                body = content
                date = ""
                note_type = "Note"
                title = note_file.stem
        else:
            body = content
            date = ""
            note_type = "Note"
            title = note_file.stem

        # Generate preview (first 150 chars of body)
        preview = body[:150].replace('\n', ' ').strip()
        if len(body) > 150:
            preview += "..."

        notes.append({
            "filename": note_file.name,
            "date": date,
            "type": note_type,
            "title": title,
            "content": body,
            "preview": preview
        })

    return notes


def delete_note(project_id: str, filename: str) -> str:
    """
    Delete a note by its filename.

    Args:
        project_id: The project ID
        filename: The note filename (e.g., "20251227-143900.md")

    Returns:
        Success or error message
    """
    notes_dir = _get_project_notes_dir(project_id)
    note_file = notes_dir / filename

    if not note_file.exists():
        return f"Note not found: {filename}"

    note_file.unlink()

    # Remove directory if empty
    if notes_dir.exists() and not any(notes_dir.iterdir()):
        notes_dir.rmdir()

    return "Note deleted successfully"


def add_project_note(
    project_id: str,
    title: str,
    content: str,
    note_type: str = "note"
) -> str:
    """
    Add a new note to a project.

    Args:
        project_id: The project ID
        title: Note title/subject
        content: Note content (markdown supported)
        note_type: Type of note - note, research, update, decision

    Returns:
        Success message
    """
    notes_dir = _get_project_notes_dir(project_id)
    notes_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    filename = now.strftime("%Y%m%d-%H%M%S.md")

    # Format with YAML frontmatter
    type_label = note_type.title() if note_type != "note" else "Note"
    note_content = f"""---
date: {timestamp}
type: {type_label}
title: {title}
---

{content}
"""

    note_file = notes_dir / filename
    note_file.write_text(note_content)

    return f"Added note to project: {title}"


# Backwards compatibility alias
def prepend_project_note(
    project_id: str,
    title: str,
    content: str,
    note_type: str = "note"
) -> str:
    """Alias for add_project_note (backwards compatibility)."""
    return add_project_note(project_id, title, content, note_type)


def append_research_result(
    project_id: str,
    task_description: str,
    summary: str,
    details: str,
    sources: Optional[list] = None
) -> str:
    """
    Append research result as structured note entry.

    This is specifically for Worker agent research tasks that are
    auto-executed and need structured formatting.

    Args:
        project_id: The project ID
        task_description: The original task that was researched
        summary: Brief summary of findings
        details: Detailed findings
        sources: List of source URLs or references

    Returns:
        Success message
    """
    # Build the content
    content_parts = [
        "[Auto-generated by Worker Agent]\n",
        "### Summary\n",
        summary + "\n",
        "\n### Details\n",
        details
    ]

    if sources:
        content_parts.append("\n\n### Sources\n")
        for source in sources:
            content_parts.append(f"- {source}\n")

    content = "".join(content_parts)

    return prepend_project_note(
        project_id=project_id,
        title=task_description[:80],  # Truncate long task descriptions
        content=content,
        note_type="research"
    )


def create_project(
    title: str,
    description: str,
    project_type: str = "goal",
    priority: str = "normal",
    deadline: Optional[str] = None,
    someday: bool = False,
    review_frequency: str = "weekly",
    values_alignment: Optional[list] = None,
    source_agent: str = "user",
    source_context: str = ""
) -> str:
    """
    Create a new project.

    Args:
        title: Project title
        description: What this project is about
        project_type: Type of project - learning, habit, goal, maintenance
        priority: high, normal, or low
        deadline: Optional ISO date string for completion target
        someday: Mark as "someday" project (no specific deadline)
        review_frequency: How often to review - daily, weekly, monthly
        values_alignment: List of values this project aligns with
        source_agent: Which agent created this (user, friend, curator, etc.)
        source_context: Additional context about why it was created

    Returns:
        Success message with project ID
    """
    project_id = _generate_id()
    now = datetime.now().isoformat()

    project = {
        "id": project_id,
        "created": now,
        "updated": now,
        "title": title,
        "description": description,
        "type": project_type,
        "status": "active",
        "priority": priority,
        "source": {
            "agent": source_agent,
            "context": source_context
        },
        "milestones": [],
        "values_alignment": values_alignment or [],
        "deadline": deadline,
        "someday": someday,
        "review_frequency": review_frequency,
        "last_reviewed": None,
        "archived": False,
        "meta": {
            "total_tasks_created": 0,
            "tasks_completed": 0,
            "estimated_hours": 0,
            "logged_hours": 0
        }
    }

    # Save project file
    project_file = PROJECTS_DIR / f"{project_id}.json"
    with open(project_file, 'w') as f:
        json.dump(project, f, indent=2)

    # Update index
    _update_index(project)

    return f"Created project '{title}' (ID: {project_id})"


def get_projects(
    status: str = "active",
    project_type: Optional[str] = None,
    include_archived: bool = False
) -> str:
    """
    Get projects, optionally filtered.

    Args:
        status: Filter by status - active, paused, completed, or all
        project_type: Filter by type - learning, habit, goal, maintenance
        include_archived: Include archived projects

    Returns:
        Formatted list of projects
    """
    index = _load_index()
    projects = index["projects"]

    # Filter by status
    if status != "all":
        projects = [p for p in projects if p["status"] == status]

    # Filter by type
    if project_type:
        projects = [p for p in projects if p.get("type") == project_type]

    # Exclude archived unless requested
    if not include_archived:
        # Load full project to check archived status
        filtered = []
        for p in projects:
            project_file = PROJECTS_DIR / f"{p['id']}.json"
            if project_file.exists():
                with open(project_file, 'r') as f:
                    full = json.load(f)
                if not full.get("archived", False):
                    filtered.append(p)
        projects = filtered

    if not projects:
        return f"No {status} projects found."

    # Sort by priority then deadline
    priority_order = {"high": 0, "normal": 1, "low": 2}
    projects.sort(key=lambda p: (
        priority_order.get(p.get("priority", "normal"), 1),
        p.get("deadline") or "9999-12-31"
    ))

    output = [f"## {status.title()} Projects ({len(projects)})\n"]
    for p in projects:
        deadline_str = f" (due: {p['deadline']})" if p.get("deadline") else ""
        priority_str = f" [{p['priority'].upper()}]" if p.get("priority") == "high" else ""
        output.append(f"- **{p['title']}**{priority_str}{deadline_str}")
        output.append(f"  Type: {p.get('type', 'goal')} | ID: {p['id']}")

    return "\n".join(output)


def get_projects_data(
    status: str = "active",
    project_type: Optional[str] = None,
    include_archived: bool = False,
    include_description: bool = True
) -> list:
    """
    Get projects as raw data for API consumption.

    Args:
        status: Filter by status - active, paused, completed, or all
        project_type: Filter by type
        include_archived: Include archived projects
        include_description: Include full description field (loads from file)

    Returns:
        List of project dictionaries
    """
    index = _load_index()
    projects = index["projects"]

    # Filter by status
    if status != "all":
        projects = [p for p in projects if p["status"] == status]

    # Filter by type
    if project_type:
        projects = [p for p in projects if p.get("type") == project_type]

    # Load full project data if needed (for descriptions and archive check)
    result = []
    for p in projects:
        project_file = PROJECTS_DIR / f"{p['id']}.json"
        if project_file.exists():
            with open(project_file, 'r') as f:
                full = json.load(f)
            # Skip archived unless requested
            if not include_archived and full.get("archived", False):
                continue
            # Add description if requested
            if include_description:
                p = p.copy()
                p["description"] = full.get("description", "")
                p["someday"] = full.get("someday", False)
            result.append(p)
        elif include_archived:
            # Try archive directory
            archive_file = ARCHIVE_DIR / f"{p['id']}.json"
            if archive_file.exists():
                with open(archive_file, 'r') as f:
                    full = json.load(f)
                if include_description:
                    p = p.copy()
                    p["description"] = full.get("description", "")
                    p["someday"] = full.get("someday", False)
                result.append(p)

    # Sort projects: General first, user projects middle (by priority/deadline), system projects last
    def project_sort_key(p):
        pid = p.get("id", "")
        # General always first
        if pid == GENERAL_PROJECT_ID:
            return (0, 0, "")
        # Notifications and Recommendations last
        if pid == NOTIFICATIONS_PROJECT_ID:
            return (2, 0, "")
        if pid == RECOMMENDATIONS_PROJECT_ID:
            return (2, 1, "")
        # User projects sorted by priority then deadline
        priority_order = {"high": 0, "normal": 1, "low": 2}
        return (1, priority_order.get(p.get("priority", "normal"), 1), p.get("deadline") or "9999-12-31")

    result.sort(key=project_sort_key)

    return result


def get_project(project_id: str) -> str:
    """
    Get details of a specific project.

    Args:
        project_id: The project ID

    Returns:
        Formatted project details
    """
    project_file = PROJECTS_DIR / f"{project_id}.json"

    if not project_file.exists():
        # Try archive
        archive_file = ARCHIVE_DIR / f"{project_id}.json"
        if archive_file.exists():
            project_file = archive_file
        else:
            return f"Project not found: {project_id}"

    with open(project_file, 'r') as f:
        project = json.load(f)

    output = [
        f"# {project['title']}",
        f"**Status:** {project['status']} | **Priority:** {project['priority']} | **Type:** {project['type']}",
        f"**Created:** {project['created'][:10]}",
    ]

    if project.get("deadline"):
        output.append(f"**Deadline:** {project['deadline']}")

    output.append(f"\n{project['description']}")

    if project.get("values_alignment"):
        output.append(f"\n**Values:** {', '.join(project['values_alignment'])}")

    if project.get("milestones"):
        output.append("\n## Milestones")
        for m in project["milestones"]:
            status_icon = "x" if m["status"] == "completed" else " "
            target = f" (target: {m['target_date']})" if m.get("target_date") else ""
            output.append(f"- [{status_icon}] {m['title']}{target}")

    meta = project.get("meta", {})
    if meta.get("total_tasks_created", 0) > 0:
        output.append(f"\n**Progress:** {meta.get('tasks_completed', 0)}/{meta.get('total_tasks_created', 0)} tasks completed")

    output.append(f"\n*ID: {project['id']}*")

    return "\n".join(output)


def update_project(
    project_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    deadline: Optional[str] = None,
    review_frequency: Optional[str] = None,
    values_alignment: Optional[list] = None
) -> str:
    """
    Update project details.

    Args:
        project_id: The project ID
        title: New title (optional)
        description: New description (optional)
        status: New status - active, paused, completed (optional)
        priority: New priority (optional)
        deadline: New deadline (optional)
        review_frequency: New review frequency (optional)
        values_alignment: New values list (optional)

    Returns:
        Success message
    """
    project_file = PROJECTS_DIR / f"{project_id}.json"

    if not project_file.exists():
        return f"Project not found: {project_id}"

    with open(project_file, 'r') as f:
        project = json.load(f)

    # Update provided fields
    if title is not None:
        project["title"] = title
    if description is not None:
        project["description"] = description
    if status is not None:
        project["status"] = status
    if priority is not None:
        project["priority"] = priority
    if deadline is not None:
        project["deadline"] = deadline
    if review_frequency is not None:
        project["review_frequency"] = review_frequency
    if values_alignment is not None:
        project["values_alignment"] = values_alignment

    project["updated"] = datetime.now().isoformat()

    # Save
    with open(project_file, 'w') as f:
        json.dump(project, f, indent=2)

    # Update index
    _update_index(project)

    return f"Updated project '{project['title']}'"


def update_project_when(
    project_id: str,
    when_type: str,
    date: Optional[str] = None
) -> str:
    """
    Update project's "when" scheduling (deadline and someday flag).

    Args:
        project_id: The project ID to update
        when_type: One of "today", "date", "someday", "anytime", "clear"
        date: ISO format date (required when when_type is "date")

    Returns:
        Success message
    """
    project_file = PROJECTS_DIR / f"{project_id}.json"

    if not project_file.exists():
        return f"Project not found: {project_id}"

    with open(project_file, 'r') as f:
        project = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")

    if when_type == "today":
        project["deadline"] = today
        project["someday"] = False
    elif when_type == "date":
        if not date:
            return "Date required for 'date' when_type"
        project["deadline"] = date
        project["someday"] = False
    elif when_type == "someday":
        project["deadline"] = None
        project["someday"] = True
    elif when_type == "anytime":
        project["deadline"] = None
        project["someday"] = False
    elif when_type == "clear":
        project["deadline"] = None
        project["someday"] = False
    else:
        return f"Invalid when_type: {when_type}"

    project["updated"] = datetime.now().isoformat()

    # Save
    with open(project_file, 'w') as f:
        json.dump(project, f, indent=2)

    # Update index
    _update_index(project)

    return f"Updated project when to: {when_type}" + (f" ({date})" if date else "")


def add_milestone(
    project_id: str,
    title: str,
    target_date: Optional[str] = None
) -> str:
    """
    Add a milestone to a project.

    Args:
        project_id: The project ID
        title: Milestone title
        target_date: Optional target date (ISO format)

    Returns:
        Success message
    """
    project_file = PROJECTS_DIR / f"{project_id}.json"

    if not project_file.exists():
        return f"Project not found: {project_id}"

    with open(project_file, 'r') as f:
        project = json.load(f)

    milestone_id = f"milestone-{len(project['milestones']) + 1:03d}"

    project["milestones"].append({
        "id": milestone_id,
        "title": title,
        "target_date": target_date,
        "status": "pending",
        "created": datetime.now().isoformat()
    })

    project["updated"] = datetime.now().isoformat()

    with open(project_file, 'w') as f:
        json.dump(project, f, indent=2)

    return f"Added milestone '{title}' to project"


def complete_milestone(project_id: str, milestone_id: str) -> str:
    """
    Mark a milestone as completed.

    Args:
        project_id: The project ID
        milestone_id: The milestone ID

    Returns:
        Success message
    """
    project_file = PROJECTS_DIR / f"{project_id}.json"

    if not project_file.exists():
        return f"Project not found: {project_id}"

    with open(project_file, 'r') as f:
        project = json.load(f)

    for milestone in project["milestones"]:
        if milestone["id"] == milestone_id:
            milestone["status"] = "completed"
            milestone["completed_at"] = datetime.now().isoformat()
            break
    else:
        return f"Milestone not found: {milestone_id}"

    project["updated"] = datetime.now().isoformat()

    with open(project_file, 'w') as f:
        json.dump(project, f, indent=2)

    return f"Completed milestone"


def archive_project(
    project_id: str,
    reason: str = "",
    outcome: str = "completed"
) -> str:
    """
    Archive a project with behavioral context.

    Args:
        project_id: The project ID
        reason: Optional reason for archiving
        outcome: Outcome type - completed, abandoned, paused, superseded

    Returns:
        Success message
    """
    project_file = PROJECTS_DIR / f"{project_id}.json"

    if not project_file.exists():
        return f"Project not found: {project_id}"

    with open(project_file, 'r') as f:
        project = json.load(f)

    # Calculate behavioral metadata
    meta = project.get("meta", {})
    tasks_completed = meta.get("tasks_completed", 0)
    total_tasks = meta.get("total_tasks_created", 0)

    # Count incomplete tasks
    from .task import _load_queue
    queue = _load_queue()
    incomplete_tasks = len([
        t for t in queue["tasks"]
        if t.get("project_id") == project_id and t.get("status") != "completed"
    ])

    # Calculate age
    created = datetime.fromisoformat(project["created"])
    age_days = (datetime.now() - created).days

    project["archived"] = True
    project["archived_at"] = datetime.now().isoformat()
    project["updated"] = datetime.now().isoformat()

    # Add behavioral archive metadata
    project["archive_metadata"] = {
        "archived_at": datetime.now().isoformat(),
        "outcome": outcome,
        "reason": reason,
        "completion_rate": tasks_completed / total_tasks if total_tasks > 0 else 0,
        "tasks_abandoned": incomplete_tasks,
        "age_days": age_days
    }

    # Move to archive directory
    archive_file = ARCHIVE_DIR / f"{project_id}.json"
    with open(archive_file, 'w') as f:
        json.dump(project, f, indent=2)

    # Remove from active projects
    project_file.unlink()

    # Update index
    _update_index(project, remove=True)

    outcome_label = outcome.title()
    return f"Archived project '{project['title']}' (outcome: {outcome_label})"


def delete_project(project_id: str, delete_tasks: bool = True) -> str:
    """
    Permanently delete a project.

    Args:
        project_id: The project ID
        delete_tasks: Also delete all tasks associated with this project

    Returns:
        Success message
    """
    project_file = PROJECTS_DIR / f"{project_id}.json"
    archive_file = ARCHIVE_DIR / f"{project_id}.json"

    project = None
    title = project_id

    # Try to load from active projects
    if project_file.exists():
        with open(project_file, 'r') as f:
            project = json.load(f)
        title = project.get("title", project_id)
        project_file.unlink()
        _update_index(project, remove=True)

    # Also remove from archive if exists
    if archive_file.exists():
        if project is None:
            with open(archive_file, 'r') as f:
                project = json.load(f)
            title = project.get("title", project_id)
        archive_file.unlink()

    if project is None:
        return f"Project not found: {project_id}"

    # Delete associated tasks if requested
    deleted_tasks = 0
    if delete_tasks:
        from .task import _load_queue, _save_queue
        queue = _load_queue()
        original_count = len(queue["tasks"])
        queue["tasks"] = [t for t in queue["tasks"] if t.get("project_id") != project_id]
        deleted_tasks = original_count - len(queue["tasks"])
        if deleted_tasks > 0:
            _save_queue(queue)

    if deleted_tasks > 0:
        return f"Deleted project '{title}' and {deleted_tasks} associated task(s)"
    return f"Deleted project '{title}'"


def get_projects_with_deadlines(days: int = 7) -> list:
    """
    Get projects with deadlines in the next N days.

    Args:
        days: Number of days to look ahead

    Returns:
        List of project dicts with upcoming deadlines
    """
    from datetime import timedelta

    index = _load_index()
    upcoming = []
    now = datetime.now()
    cutoff = now + timedelta(days=days)

    for p in index["projects"]:
        if p.get("deadline") and p.get("status") == "active":
            try:
                deadline = datetime.fromisoformat(p["deadline"])
                if now <= deadline <= cutoff:
                    upcoming.append(p)
            except (ValueError, TypeError):
                pass

    # Sort by deadline
    upcoming.sort(key=lambda p: p["deadline"])
    return upcoming


def increment_task_count(project_id: str, completed: bool = False) -> str:
    """
    Increment task counters for a project.

    Args:
        project_id: The project ID
        completed: If True, increment completed count too

    Returns:
        Success message
    """
    project_file = PROJECTS_DIR / f"{project_id}.json"

    if not project_file.exists():
        return f"Project not found: {project_id}"

    with open(project_file, 'r') as f:
        project = json.load(f)

    if "meta" not in project:
        project["meta"] = {"total_tasks_created": 0, "tasks_completed": 0}

    if not completed:
        project["meta"]["total_tasks_created"] = project["meta"].get("total_tasks_created", 0) + 1
    else:
        project["meta"]["tasks_completed"] = project["meta"].get("tasks_completed", 0) + 1

    project["updated"] = datetime.now().isoformat()

    with open(project_file, 'w') as f:
        json.dump(project, f, indent=2)

    return "Updated project task counts"


# Tool definitions for agents
PROJECT_TOOLS = [
    {
        "name": "create_project",
        "description": "Create a new project for ongoing goals. Use this when the user wants to track a multi-step goal like learning a skill, building a habit, or completing a major objective.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short project title (2-5 words, e.g., 'Learn Spanish', 'Morning Routine')"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the project goals, scope, and why it matters. Can be multiple sentences."
                },
                "project_type": {
                    "type": "string",
                    "enum": ["learning", "habit", "goal", "maintenance"],
                    "description": "Type of project"
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "normal", "low"],
                    "description": "Priority level"
                },
                "deadline": {
                    "type": "string",
                    "description": "Target completion date (ISO format: YYYY-MM-DD)"
                },
                "someday": {
                    "type": "boolean",
                    "description": "Mark as 'someday' project (no specific deadline). Default: false"
                },
                "review_frequency": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly"],
                    "description": "How often to review progress"
                },
                "values_alignment": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of values this project aligns with"
                }
            },
            "required": ["title", "description"]
        }
    },
    {
        "name": "get_projects",
        "description": "Get a list of projects, optionally filtered by status or type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "completed", "all"],
                    "description": "Filter by status (default: active)"
                },
                "project_type": {
                    "type": "string",
                    "enum": ["learning", "habit", "goal", "maintenance"],
                    "description": "Filter by type"
                },
                "include_archived": {
                    "type": "boolean",
                    "description": "Include archived projects"
                }
            }
        }
    },
    {
        "name": "get_project",
        "description": "Get details of a specific project including milestones and progress.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The project ID"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "update_project",
        "description": "Update project details like title, description, status, priority, or deadline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The project ID"
                },
                "title": {
                    "type": "string",
                    "description": "Short project title (2-5 words)"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed project description"
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "completed"]
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "normal", "low"]
                },
                "deadline": {"type": "string"},
                "review_frequency": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly"]
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "add_milestone",
        "description": "Add a milestone to a project to track major progress points.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The project ID"
                },
                "title": {
                    "type": "string",
                    "description": "Milestone title"
                },
                "target_date": {
                    "type": "string",
                    "description": "Target date (ISO format)"
                }
            },
            "required": ["project_id", "title"]
        }
    },
    {
        "name": "archive_project",
        "description": "Archive a project with behavioral context tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The project ID"
                },
                "reason": {
                    "type": "string",
                    "description": "Optional reason for archiving"
                },
                "outcome": {
                    "type": "string",
                    "enum": ["completed", "abandoned", "paused", "superseded"],
                    "description": "Outcome type (default: completed)"
                }
            },
            "required": ["project_id"]
        }
    },
    {
        "name": "delete_project",
        "description": "Permanently delete a project and optionally its associated tasks. Use for cleanup or removing test projects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The project ID"
                },
                "delete_tasks": {
                    "type": "boolean",
                    "description": "Also delete all tasks associated with this project (default: true)"
                }
            },
            "required": ["project_id"]
        }
    }
]

PROJECT_HANDLERS = {
    "create_project": create_project,
    "get_projects": get_projects,
    "get_project": get_project,
    "update_project": update_project,
    "add_milestone": add_milestone,
    "archive_project": archive_project,
    "delete_project": delete_project,
}
