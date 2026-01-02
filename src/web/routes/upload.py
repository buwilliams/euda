"""
Upload API Route

Handles file uploads by:
1. Creating an ingest job for the archivist
2. Saving the file as an asset attached to that job
"""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from ...tools.jobs import create_job
from ...tools.assets import ASSETS_DIR


router = APIRouter()


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for processing.

    Creates an ingest job and saves the file as an asset.
    The archivist will process the file and add it to the lifelog.
    """
    # Create an ingest job for the archivist
    job = create_job(
        name=f"Ingest: {file.filename}",
        description=f"Process uploaded file: {file.filename}",
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
        "message": f"File queued for processing. The archivist will review it shortly."
    }
