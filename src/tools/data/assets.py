"""
Asset Tools - Manage files and assets attached to jobs.
"""

import base64
import mimetypes
from pathlib import Path
from typing import List, Optional

from .. import tool


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
ASSETS_DIR = DATA_DIR / "jobs" / "assets"


def _get_job_assets_dir(job_id: str) -> Path:
    """Get the assets directory for a job."""
    return ASSETS_DIR / job_id


@tool("list_assets", "List all assets attached to a job. Use when: checking what files are attached to a job.", tool_type="data")
def list_assets(job_id: str) -> List[dict]:
    """List assets attached to a job."""
    assets_dir = _get_job_assets_dir(job_id)

    if not assets_dir.exists():
        return []

    assets = []
    for path in assets_dir.iterdir():
        if path.is_file():
            mime_type, _ = mimetypes.guess_type(str(path))
            assets.append({
                "filename": path.name,
                "size": path.stat().st_size,
                "mime_type": mime_type
            })

    return assets


@tool("read_asset", "Read an asset's content (text files only). Use when: viewing job attachments or context files.", tool_type="data")
def read_asset(job_id: str, filename: str) -> Optional[dict]:
    """Read an asset's content."""
    path = _get_job_assets_dir(job_id) / filename

    if not path.exists():
        return {"error": f"Asset not found: {filename}"}

    # Check if it's a text file
    mime_type, _ = mimetypes.guess_type(str(path))
    is_text = mime_type and (
        mime_type.startswith("text/") or
        mime_type in ["application/json", "application/xml"]
    )

    if is_text:
        return {
            "filename": filename,
            "content": path.read_text(),
            "mime_type": mime_type
        }
    else:
        # Return metadata only for binary files
        return {
            "filename": filename,
            "size": path.stat().st_size,
            "mime_type": mime_type,
            "note": "Binary file - content not included"
        }


@tool("write_asset", "Write content to an asset file. Use when: storing files, notes, or data related to a job.", tool_type="data")
def write_asset(job_id: str, filename: str, content: str) -> dict:
    """Write content to an asset file."""
    assets_dir = _get_job_assets_dir(job_id)
    assets_dir.mkdir(parents=True, exist_ok=True)

    path = assets_dir / filename
    path.write_text(content)

    return {
        "filename": filename,
        "size": path.stat().st_size,
        "status": "created" if not path.exists() else "updated"
    }


@tool("delete_asset", "Delete an asset from a job. Use when: removing outdated or unwanted attachments.", tool_type="data")
def delete_asset(job_id: str, filename: str) -> dict:
    """Delete an asset."""
    path = _get_job_assets_dir(job_id) / filename

    if not path.exists():
        return {"error": f"Asset not found: {filename}"}

    path.unlink()
    return {"filename": filename, "status": "deleted"}
