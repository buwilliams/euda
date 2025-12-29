"""
Euno - Web API

FastAPI application for the Interaction Agent and other endpoints.
SSE support for real-time updates.
"""

import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth import is_password_set, validate_session
from .routes import (
    auth_router, chat_router, tasks_router, projects_router,
    context_router, identity_router, admin_router
)
from .routes.admin import watch_tasks, watch_projects


# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
STATIC_DIR = BASE_DIR / "static"


# Paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/app",
    "/api/auth/login",
    "/api/auth/check",
    "/api/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def get_session_token(request: Request) -> Optional[str]:
    """Extract session token from cookie or Authorization header."""
    token = request.cookies.get("euno_session")
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


# ============== Lifespan Management ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage background tasks on startup/shutdown."""
    tasks_watcher_task = asyncio.create_task(watch_tasks())
    projects_watcher_task = asyncio.create_task(watch_projects())

    yield

    tasks_watcher_task.cancel()
    projects_watcher_task.cancel()


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Euno",
    description="AI Personal Assistant API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ============== Authentication Middleware ==============

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Check authentication for protected routes."""
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    if request.url.path.startswith("/static"):
        return await call_next(request)

    if not is_password_set():
        return await call_next(request)

    token = get_session_token(request)
    if not token or not validate_session(token):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"}
        )

    return await call_next(request)


# ============== Register Routes ==============

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(tasks_router)
app.include_router(projects_router)
app.include_router(context_router)
app.include_router(identity_router)
app.include_router(admin_router)


# ============== Legacy Endpoints ==============

@app.get("/logs/{date}")
async def get_log_legacy(date: str):
    """Legacy log endpoint for compatibility."""
    from .routes.identity import get_log
    return await get_log(date)
