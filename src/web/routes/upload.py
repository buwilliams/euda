"""
Upload API Route

Handles file uploads by:
1. Finding the Archivist's inbox job (under Agents)
2. Creating an ingest job per file as a child of Archivist's inbox
3. Saving the file as an asset attached to that job
4. Triggering the Archivist via job:assigned
"""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from ...tools.jobs import create_job, get_agent_inbox_job
from ...tools.assets import ASSETS_DIR


router = APIRouter()


def get_archivist_inbox() -> dict:
    """Get the Archivist's inbox job for uploaded files."""
    inbox = get_agent_inbox_job("archivist")
    if not inbox:
        raise RuntimeError("Archivist inbox not found. Ensure agents are synced.")
    return inbox


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for processing.

    Creates an ingest job under the Archivist's inbox and saves the file as an asset.
    The Archivist will process the file and add it to the lifelog.
    """
    # Get the Archivist's inbox
    archivist_inbox = get_archivist_inbox()

    # Create an ingest job as a child of Archivist's inbox
    job = create_job(
        name=f"Ingest: {file.filename}",
        description=f"Process uploaded file: {file.filename}",
        parent_id=archivist_inbox["id"],
        assignees=["archivist"],
        created_by="user"
    )

    job_id = job["id"]

    # Save file as asset
    assets_dir = ASSETS_DIR / job_id
    assets_dir.mkdir(parents=True, exist_ok=True)

    file_path = assets_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "job_id": job_id,
        "archivist_inbox_id": archivist_inbox["id"],
        "message": "File queued for processing. The Archivist will review it shortly."
    }
