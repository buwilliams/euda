"""
Notes Tools - Manage notes attached to jobs.

Notes are stored as markdown files in data/notes/{job_id}/
Each note is a separate .md file with the format: {title}-{date}.md
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from . import tool


DATA_DIR = Path(__file__).parent.parent.parent / "data"
NOTES_DIR = DATA_DIR / "jobs" / "notes"


def _get_job_notes_dir(job_id: str) -> Path:
    """Get the notes directory for a job."""
    return NOTES_DIR / job_id


def _sanitize_filename(title: str) -> str:
    """Convert title to safe filename."""
    # Remove special characters, replace spaces with hyphens
    safe = re.sub(r'[^\w\s-]', '', title.lower())
    safe = re.sub(r'[-\s]+', '-', safe).strip('-')
    return safe[:50]  # Limit length


def _parse_note_file(path: Path) -> dict:
    """Parse a note file and return metadata."""
    content = path.read_text()

    # Extract title from first line (# Title) or use filename
    lines = content.split('\n')
    title = path.stem
    if lines and lines[0].startswith('# '):
        title = lines[0][2:].strip()

    return {
        "id": path.stem,
        "title": title,
        "filename": path.name,
        "size": path.stat().st_size,
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat() + "Z",
        "created_at": datetime.fromtimestamp(path.stat().st_ctime).isoformat() + "Z"
    }


@tool("list_notes", "List all notes for a job")
def list_notes(job_id: str) -> List[dict]:
    """List notes attached to a job."""
    notes_dir = _get_job_notes_dir(job_id)

    if not notes_dir.exists():
        return []

    notes = []
    for path in sorted(notes_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        notes.append(_parse_note_file(path))

    return notes


@tool("read_note", "Read a note's content")
def read_note(job_id: str, note_id: str) -> Optional[dict]:
    """Read a note's content."""
    notes_dir = _get_job_notes_dir(job_id)
    path = notes_dir / f"{note_id}.md"

    if not path.exists():
        return {"error": f"Note not found: {note_id}"}

    content = path.read_text()
    meta = _parse_note_file(path)
    meta["content"] = content

    return meta


@tool("create_note", "Create a new note for a job")
def create_note(job_id: str, title: str, content: str, agent: str = "user") -> dict:
    """Create a new note for a job."""
    notes_dir = _get_job_notes_dir(job_id)
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from title and date
    date_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_title = _sanitize_filename(title)
    filename = f"{safe_title}-{date_str}.md"

    path = notes_dir / filename

    # Format content with title header and metadata
    full_content = f"# {title}\n\n"
    full_content += f"*Created by {agent} on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
    full_content += content

    path.write_text(full_content)

    return _parse_note_file(path)


@tool("update_note", "Update an existing note")
def update_note(job_id: str, note_id: str, content: str) -> Optional[dict]:
    """Update an existing note's content."""
    notes_dir = _get_job_notes_dir(job_id)
    path = notes_dir / f"{note_id}.md"

    if not path.exists():
        return {"error": f"Note not found: {note_id}"}

    path.write_text(content)

    return _parse_note_file(path)


@tool("delete_note", "Delete a note")
def delete_note(job_id: str, note_id: str) -> dict:
    """Delete a note."""
    notes_dir = _get_job_notes_dir(job_id)
    path = notes_dir / f"{note_id}.md"

    if not path.exists():
        return {"error": f"Note not found: {note_id}"}

    path.unlink()
    return {"note_id": note_id, "status": "deleted"}
