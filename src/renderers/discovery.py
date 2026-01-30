"""
Renderer Discovery - Scan and validate renderers.

Renderers are discovered by scanning the renderers/ directory for subdirectories
that contain a manifest.json file and a component.js file.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


RENDERERS_DIR = Path(__file__).parent.parent.parent / "renderers"

# Cache for discovered renderers
_renderer_cache: Optional[List["RendererInfo"]] = None


@dataclass
class RendererInfo:
    """Information about a discovered renderer."""

    name: str
    path: Path
    description: str = ""
    display: List[str] = field(default_factory=lambda: ["embed"])
    schema: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.name}: {self.description}" if self.description else self.name

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "display": self.display,
            "schema": self.schema,
        }


def _load_manifest(manifest_path: Path) -> Optional[Dict[str, Any]]:
    """Load and parse a renderer's manifest.json.

    Args:
        manifest_path: Path to the manifest.json file

    Returns:
        Parsed manifest dict or None if invalid
    """
    try:
        content = manifest_path.read_text()
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return None


def validate_renderer(name: str) -> bool:
    """Validate that a renderer exists and has the required structure.

    A valid renderer has:
    - A directory at renderers/{name}/
    - A manifest.json file in that directory
    - A component.js file in that directory

    Args:
        name: Renderer name (directory name)

    Returns:
        True if valid, False otherwise
    """
    renderer_dir = RENDERERS_DIR / name
    manifest_path = renderer_dir / "manifest.json"
    component_path = renderer_dir / "component.js"

    if not renderer_dir.is_dir():
        return False

    if not manifest_path.is_file():
        return False

    if not component_path.is_file():
        return False

    # Validate manifest is parseable JSON
    if _load_manifest(manifest_path) is None:
        return False

    return True


def discover_renderers() -> List[RendererInfo]:
    """Scan the renderers directory and return info about valid renderers.

    Returns:
        List of RendererInfo for each valid renderer found
    """
    global _renderer_cache

    if _renderer_cache is not None:
        return _renderer_cache

    renderers = []

    if not RENDERERS_DIR.is_dir():
        return renderers

    for item in sorted(RENDERERS_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith(("_", ".")):
            if validate_renderer(item.name):
                manifest_path = item / "manifest.json"
                manifest = _load_manifest(manifest_path)

                if manifest:
                    # Extract fields from manifest with defaults
                    display = manifest.get("display", ["embed"])
                    if isinstance(display, str):
                        display = [display]

                    renderers.append(
                        RendererInfo(
                            name=item.name,
                            path=item,
                            description=manifest.get("description", ""),
                            display=display,
                            schema=manifest.get("schema", {}),
                        )
                    )

    _renderer_cache = renderers
    return renderers


def get_renderer_info(name: str) -> Optional[RendererInfo]:
    """Get information about a specific renderer.

    Args:
        name: Renderer name

    Returns:
        RendererInfo for the renderer, or None if not found/invalid
    """
    renderer_dir = RENDERERS_DIR / name

    if not renderer_dir.is_dir():
        return None

    if not validate_renderer(name):
        return None

    manifest_path = renderer_dir / "manifest.json"
    manifest = _load_manifest(manifest_path)

    if not manifest:
        return None

    display = manifest.get("display", ["embed"])
    if isinstance(display, str):
        display = [display]

    return RendererInfo(
        name=name,
        path=renderer_dir,
        description=manifest.get("description", ""),
        display=display,
        schema=manifest.get("schema", {}),
    )


def invalidate_cache():
    """Clear the renderer discovery cache.

    Call this after adding or removing renderers to force rediscovery.
    """
    global _renderer_cache
    _renderer_cache = None


def get_renderer_path(name: str) -> Optional[Path]:
    """Get the path to a renderer's directory.

    Args:
        name: Renderer name

    Returns:
        Path to renderer directory, or None if not found
    """
    renderer_dir = RENDERERS_DIR / name
    if not renderer_dir.is_dir():
        return None
    return renderer_dir
