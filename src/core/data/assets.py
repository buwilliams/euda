"""
Asset Tools - Manage files and assets attached to topics.
"""

import base64
import mimetypes
from pathlib import Path
from typing import List, Optional



DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
ASSETS_DIR = DATA_DIR / "topics" / "assets"


def _get_topic_assets_dir(topic_id: str) -> Path:
    """Get the assets directory for a topic."""
    return ASSETS_DIR / topic_id


def list_assets(topic_id: str) -> List[dict]:
    """List assets attached to a topic."""
    assets_dir = _get_topic_assets_dir(topic_id)

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


def read_asset(topic_id: str, filename: str) -> Optional[dict]:
    """Read an asset's content."""
    path = _get_topic_assets_dir(topic_id) / filename

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


def write_asset(topic_id: str, filename: str, content: str) -> dict:
    """Write content to an asset file."""
    assets_dir = _get_topic_assets_dir(topic_id)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Normalize escaped newlines from LLM output (converts literal \n to actual newlines)
    normalized_content = content.replace('\\n', '\n') if content else content

    path = assets_dir / filename
    path.write_text(normalized_content)

    return {
        "filename": filename,
        "size": path.stat().st_size,
        "status": "created" if not path.exists() else "updated"
    }


def delete_asset(topic_id: str, filename: str) -> dict:
    """Delete an asset."""
    path = _get_topic_assets_dir(topic_id) / filename

    if not path.exists():
        return {"error": f"Asset not found: {filename}"}

    path.unlink()
    return {"filename": filename, "status": "deleted"}


def list_recent_assets(limit: int = 50) -> List[dict]:
    """List recent assets across all topics, sorted by modification time.

    Returns a list of assets with topic_id included for navigation.
    """
    if not ASSETS_DIR.exists():
        return []

    all_assets = []

    # Iterate through all topic asset directories
    for topic_dir in ASSETS_DIR.iterdir():
        if not topic_dir.is_dir():
            continue

        topic_id = topic_dir.name

        for path in topic_dir.iterdir():
            if path.is_file():
                mime_type, _ = mimetypes.guess_type(str(path))
                stat = path.stat()
                all_assets.append({
                    "topic_id": topic_id,
                    "filename": path.name,
                    "size": stat.st_size,
                    "mime_type": mime_type,
                    "modified_at": stat.st_mtime
                })

    # Sort by modification time (most recent first)
    all_assets.sort(key=lambda x: x["modified_at"], reverse=True)

    # Return limited results (remove internal modified_at timestamp)
    return [
        {k: v for k, v in asset.items() if k != "modified_at"}
        for asset in all_assets[:limit]
    ]


def write_asset_bytes(topic_id: str, filename: str, content: bytes) -> dict:
    """Write binary content to an asset file (internal use).

    This is not a tool - it's used by the upload endpoint to save uploaded files.
    """
    assets_dir = _get_topic_assets_dir(topic_id)
    assets_dir.mkdir(parents=True, exist_ok=True)

    path = assets_dir / filename
    path.write_bytes(content)

    return {
        "filename": filename,
        "size": len(content),
        "path": str(path.relative_to(DATA_DIR))
    }
