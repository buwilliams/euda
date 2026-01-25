"""
FastAPI Web Application

Provides REST API for the Euno system.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.gzip import GZipMiddleware

from .routes import topics, agents, chat, user, auth, system, upload, transcribe, synthesize, assets
from .routes.auth import get_session_token
from .auth import is_password_set, verify_session
from .events import trigger_shutdown


# Paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/api/auth/check",
    "/api/auth/login",
    "/api/health",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown."""
    # Startup - ensure system containers exist
    from ..tools.data.topics import get_agents_container, get_projects_container, get_assets_container
    get_agents_container()
    get_projects_container()
    get_assets_container()
    yield
    # Shutdown - signal all SSE connections to close
    trigger_shutdown()


app = FastAPI(
    title="Euno",
    description="Personal Intelligence System",
    version="3.0.0",
    lifespan=lifespan
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=500)


# Authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Check authentication for protected routes."""
    path = request.url.path

    # Allow public paths
    if path in PUBLIC_PATHS:
        return await call_next(request)

    # Allow web files
    if path.startswith("/web"):
        return await call_next(request)

    # If no password set, allow all
    if not is_password_set():
        return await call_next(request)

    # Check session
    token = get_session_token(request)
    if not token or not verify_session(token):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"}
        )

    return await call_next(request)


# Include routers
app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(transcribe.router, prefix="/api/transcribe", tags=["transcribe"])
app.include_router(synthesize.router, prefix="/api/synthesize", tags=["synthesize"])

# Serve web files
web_dir = Path(__file__).parent / "frontend"
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")

    @app.get("/")
    def serve_index():
        return FileResponse(web_dir / "index.html")
