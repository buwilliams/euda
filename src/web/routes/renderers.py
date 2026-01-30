"""
Renderer API Routes - Discovery and file serving for pluggable UI components.

Renderers are discovered from the renderers/ directory and provide
rich UI components that the frontend can dynamically load.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from src.renderers import (
    discover_renderers,
    get_renderer_info,
    get_renderer_path,
    invalidate_cache,
    RENDERERS_DIR,
)


router = APIRouter()


@router.get("")
def list_renderers():
    """List all available renderers.

    Returns renderer metadata from manifest.json files.
    """
    renderers = discover_renderers()
    return {
        "renderers": [r.to_dict() for r in renderers],
        "count": len(renderers),
    }


@router.get("/{name}")
def get_renderer(name: str):
    """Get metadata for a specific renderer.

    Args:
        name: Renderer name (directory name)

    Returns:
        Renderer metadata from manifest.json
    """
    renderer = get_renderer_info(name)
    if not renderer:
        raise HTTPException(status_code=404, detail=f"Renderer not found: {name}")

    return renderer.to_dict()


@router.get("/{name}/{file_path:path}")
def serve_renderer_file(name: str, file_path: str):
    """Serve a file from a renderer's directory.

    This enables the frontend to dynamically import renderer components:
    - component.js - The main renderer module
    - manifest.json - Renderer metadata
    - Any additional assets (CSS, images, etc.)

    Args:
        name: Renderer name (directory name)
        file_path: Path to file within the renderer directory

    Returns:
        The requested file
    """
    renderer_dir = get_renderer_path(name)
    if not renderer_dir:
        raise HTTPException(status_code=404, detail=f"Renderer not found: {name}")

    # Construct full file path
    full_path = renderer_dir / file_path

    # Security: ensure the resolved path is within the renderer directory
    try:
        resolved = full_path.resolve()
        if not str(resolved).startswith(str(renderer_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Determine media type
    suffix = full_path.suffix.lower()
    media_types = {
        ".js": "application/javascript",
        ".json": "application/json",
        ".css": "text/css",
        ".html": "text/html",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    # Add cache-control headers to ensure fresh content during development
    return FileResponse(
        full_path,
        media_type=media_type,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@router.post("/refresh")
def refresh_renderers():
    """Force rediscovery of renderers.

    Call this after adding or removing renderers to update the cache.
    """
    invalidate_cache()
    renderers = discover_renderers()
    return {
        "success": True,
        "renderers": [r.to_dict() for r in renderers],
        "count": len(renderers),
    }
