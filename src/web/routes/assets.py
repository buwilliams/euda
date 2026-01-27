"""
Assets API Routes - endpoints for cross-topic asset operations
"""

from fastapi import APIRouter

from src.core.data.assets import list_recent_assets


router = APIRouter()


@router.get("/recent")
def api_list_recent_assets(limit: int = 50):
    """List recent assets across all topics.

    Returns assets sorted by modification time (most recent first).
    Each asset includes topic_id for navigation.
    """
    return list_recent_assets(limit=limit)
