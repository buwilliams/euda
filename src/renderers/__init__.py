"""
Renderer infrastructure for pluggable UI components.

Renderers are discovered from the renderers/ directory and provide
rich UI components that can be dynamically loaded by the frontend.
"""

from .discovery import (
    RendererInfo,
    discover_renderers,
    get_renderer_info,
    validate_renderer,
    invalidate_cache,
    get_renderer_path,
    RENDERERS_DIR,
)

__all__ = [
    "RendererInfo",
    "discover_renderers",
    "get_renderer_info",
    "validate_renderer",
    "invalidate_cache",
    "get_renderer_path",
    "RENDERERS_DIR",
]
