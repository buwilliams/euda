"""
Upload API Route

Handles file uploads by:
1. Finding or creating an Inbox root job
2. Creating an ingest job as a child of Inbox
3. Saving the file as an asset attached to that job
"""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from ...tools.jobs import create_job, list_jobs
from ...tools.assets import ASSETS_DIR


router = APIRouter()

# Name of the root job that holds all ingest jobs
INBOX_JOB_NAME = "Inbox"


def get_or_create_inbox_job() -> dict:
    """Find or create the Inbox root job for uploaded files."""
    # Look for existing Inbox job (root level, not archived)
    all_jobs = list_jobs()
    for job in all_jobs:
        if job["name"] == INBOX_JOB_NAME and job["parent_id"] is None and job["status"] != "archived":
            return job

    # Create new Inbox job
    return create_job(
        name=INBOX_JOB_NAME,
        description="Files uploaded for processing",
        tags=["system", "inbox"],
        created_by="system"
    )


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for processing.

    Creates an ingest job under the Inbox and saves the file as an asset.
    The archivist will process the file and add it to the lifelog.
    """
    # Get or create the Inbox parent job
    inbox = get_or_create_inbox_job()

    # Create an ingest job as a child of Inbox
    job = create_job(
        name=f"Ingest: {file.filename}",
        description=f"Process uploaded file: {file.filename}",
        parent_id=inbox["id"],
        tags=["ingest"],
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
        "inbox_id": inbox["id"],
        "message": f"File queued for processing. The archivist will review it shortly."
    }
