"""
Route modules for the Euno web API.
"""

from .auth import router as auth_router
from .chat import router as chat_router
from .tasks import router as tasks_router
from .projects import router as projects_router
from .context import router as context_router
from .identity import router as identity_router
from .admin import router as admin_router

__all__ = [
    "auth_router",
    "chat_router",
    "tasks_router",
    "projects_router",
    "context_router",
    "identity_router",
    "admin_router",
]
